from fastapi import Depends, APIRouter, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import SessionLocal
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from app.routes.auth import SECRET_KEY, ALGORITHM
from app.services.hf_client import generate_llama_response

router = APIRouter(prefix="/chat", tags=["Chat"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


MAX_HISTORY = 10


def get_current_user_id(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("id")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@router.post("/message", response_model=schemas.ChatResponse)
def chat_message(
    request: schemas.ChatRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    user_msg = request.message
    chat_id = request.chat_id

    #  Fetch last N messages from database
    history_records = (
        db.query(models.ChatHistory)
        .filter(models.ChatHistory.chat_id == chat_id, models.ChatHistory.user_id == user_id)
        .order_by(models.ChatHistory.id.desc())
        .limit(MAX_HISTORY)
        .all()
    )

    # Reverse to get chronological order (old → new)
    history_records = list(reversed(history_records))

    #  Build message context for the model  [{"role": "system", "content": "You are a concise assistant. Keep your answers short and under 3 sentences."}]
    messages = [{"role": "system", "content": "You are a friendly, concise AI shopping assistant that remembers the user's preferences and recommends products accordingly.answer in moderate short length."}]
    for record in history_records:
        messages.append({"role": "user", "content": record.message})
        messages.append({"role": "assistant", "content": record.response})
    messages.append({"role": "user", "content": user_msg})

    #  Call the LLaMA model
    bot_reply = generate_llama_response(messages)

    #  Save the new message to DB
    try:
        new_entry = models.ChatHistory(
            chat_id=chat_id,
            user_id=user_id,
            message=user_msg,
            response=bot_reply
        )
        db.add(new_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

    return {"response": bot_reply}


@router.get("/history")
def get_history(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    chats = db.query(models.ChatHistory).filter(models.ChatHistory.user_id == user_id).all()
    grouped = {}
    for c in chats:
        grouped.setdefault(c.chat_id, []).append({"from": "user", "text": c.message})
        grouped[c.chat_id].append({"from": "bot", "text": c.response})

    return [{"chat_id": k, "messages": v} for k, v in grouped.items()]
