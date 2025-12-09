/**
 * Copyright AGNTCY Contributors
 * SPDX-License-Identifier: Apache-2.0
 **/

import React, { useEffect, useRef, useState } from "react"
import { HiUser } from "react-icons/hi"
import { RiRobot2Fill } from "react-icons/ri"
import { Waveform } from "ldrs/react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import "ldrs/react/Waveform.css"

interface SlowTextProps {
  text: string
  speed?: number
}

const SlowText: React.FC<SlowTextProps> = ({ text, speed = 25 }) => {
  const [displayedText, setDisplayedText] = useState("")
  const idx = useRef(-1)

  useEffect(() => {
    function tick() {
      idx.current++
      setDisplayedText((prev) => prev + text[idx.current])
    }

    if (idx.current < text.length - 1) {
      const addChar = setInterval(tick, speed)
      return () => clearInterval(addChar)
    }
  }, [displayedText, speed, text])

  return <span>{displayedText}</span>
}

// Remove extra blank lines
function normalizeMarkdown(text: string) {
  return text
    .split("\n")
    .filter((line) => line.trim() !== "")
    .join("\n")
}

interface MessageProps {
  content: string
  aiMessage: boolean
  animate: boolean
  loading: boolean
}

const Message: React.FC<MessageProps> = ({
  content,
  aiMessage,
  animate,
  loading,
}) => {
  return (
    <div
      className={`flex w-full items-start gap-2 px-4 py-2 sm:px-6 md:px-8 lg:px-10 ${
        aiMessage ? "bg-[rgb(247,247,248)]" : ""
      }`}
    >
      <div className="flex h-[35px] w-[35px] flex-shrink-0 items-center justify-center">
        {aiMessage ? <RiRobot2Fill color="#003DA5" size={28} /> : <HiUser size={28} />}
      </div>

      <div className="ml-2 min-w-0 flex-1 break-words">
        {loading ? (
          <div style={{ opacity: 0.5 }}>
            <Waveform size="20" stroke="3.5" speed="1" color="#003DA5" />
          </div>
        ) : animate ? (
          <SlowText speed={20} text={content} />
        ) : aiMessage ? (
          <div 
            className="leading-tight"
            style={{
              lineHeight: '1.3'
            }}
          > 
            <style>{`
              .tight-markdown * {
                margin: 0 !important;
                padding: 0 !important;
                line-height: 1.3 !important;
              }
              .tight-markdown ul {
                padding-left: 1rem !important;
                margin-top: 1px !important;
              }
              .tight-markdown h2,
              .tight-markdown h3 {
                margin-top: 3px !important;
              }
            `}</style>
            <div className="tight-markdown">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  strong: ({ children }) => (
                    <strong className="font-bold text-[#FFC72C]">{children}</strong>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-base font-bold text-[#FFC72C]">
                      {children}
                    </h3>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-lg font-bold text-[#FFC72C]">
                      {children}
                    </h2>
                  ),
                  code: ({ children }) => (
                    <code className="bg-gray-800 px-1 py-0.5 rounded text-sm">
                      {children}
                    </code>
                  ),
                }}
              >
                {normalizeMarkdown(content)}
              </ReactMarkdown>
            </div>
          </div>
        ) : (
          content
        )}
      </div>
    </div>
  )
}

export default React.memo(Message)