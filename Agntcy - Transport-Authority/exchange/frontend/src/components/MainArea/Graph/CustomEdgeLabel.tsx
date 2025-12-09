/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 **/

import React from "react"
import { EdgeLabelRenderer } from "@xyflow/react"
import { cn } from "@/utils/cn.ts"

interface CustomEdgeLabelProps {
  x: number
  y: number
  label?: string
  active?: boolean
}

const CustomEdgeLabel: React.FC<CustomEdgeLabelProps> = ({
  x,
  y,
  label,
  active,
}) => {
  const isLongLabel = true

  return (
    <EdgeLabelRenderer>
      <div
        className={cn(
          "pointer-events-none absolute flex h-5 items-center justify-center rounded-lg border-none px-[5px] py-[2px] font-[Inter] text-xs font-normal leading-4 opacity-100 shadow-none",
          isLongLabel ? "w-[100px] gap-[6px]" : "w-[34px] gap-1",
          active
            ? "bg-edge-label-background-active text-edge-label-text-active"
            : "bg-edge-label-background text-edge-label-text",
        )}
        style={{
          transform: "translate(-50%, -50%)",
          left: `${x}px`,
          top: `${y}px`,
        }}
      >
        {label && (
          <div className="flex flex-shrink-0 items-center justify-center whitespace-nowrap font-[Inter] text-xs font-normal leading-4">
            {label}
          </div>
        )}
      </div>
    </EdgeLabelRenderer>
  )
}

export default CustomEdgeLabel
