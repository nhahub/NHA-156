import React from 'react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function MessageBubble({ message }) {
  const isUser = message.from === 'user'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-lg px-4 py-3 rounded-2xl shadow-sm text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? 'bg-[#C4DADE] text-[#1F3634] rounded-br-none'
            : 'bg-white text-gray-800 rounded-bl-none border border-[#C4DADE]/40'
        }`}
      >
        {isUser ? (
          // Just show plain text for user messages
          message.text
        ) : (
          // Render Markdown for bot messages
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.text}
          </ReactMarkdown>
        )}
      </div>
    </motion.div>
  )
}
