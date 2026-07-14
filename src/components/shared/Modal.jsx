import { useEffect, useState, useRef, useCallback } from 'react'

// ── resize/drag helpers ───────────────────────────────────────────────────
function useDragResize(defaultW, defaultH) {
  const [size, setSize] = useState({ w: defaultW, h: defaultH })
  const [pos, setPos]   = useState(null) // null = centered via flex; { x, y } = pinned
  const sRef = useRef(size)
  const pRef = useRef(pos)

  // sync refs
  useEffect(() => { sRef.current = size }, [size])
  useEffect(() => { pRef.current = pos },  [pos])

  // pin modal to current visual center before first drag so it doesn't jump
  const pinToCenter = useCallback(() => {
    if (pRef.current) return pRef.current
    const vw = window.innerWidth, vh = window.innerHeight
    const { w, h } = sRef.current
    const next = { x: Math.round((vw - w) / 2), y: Math.round((vh - h) / 2) }
    setPos(next)
    pRef.current = next
    return next
  }, [])

  const startResize = useCallback((dx, dy) => (e) => {
    e.preventDefault(); e.stopPropagation()
    const curPos = pinToCenter()
    const startX = e.clientX, startY = e.clientY
    const startW = sRef.current.w, startH = sRef.current.h
    const startPX = curPos.x, startPY = curPos.y
    const onMove = (ev) => {
      const dw = (ev.clientX - startX) * dx
      const dh = (ev.clientY - startY) * dy
      const w = Math.max(420, Math.min(window.innerWidth - 20, startW + dw))
      const h = Math.max(300, Math.min(window.innerHeight - 20, startH + dh))
      // when pulling left/top edge, shift position so opposite edge stays fixed
      const x = dx === -1 ? startPX + (startW - w) : startPX
      const y = dy === -1 ? startPY + (startH - h) : startPY
      sRef.current = { w, h }
      pRef.current = { x, y }
      setSize({ w, h })
      setPos({ x, y })
    }
    const onUp = () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [pinToCenter])

  const startMove = useCallback((e) => {
    if (e.target.closest('button')) return
    e.preventDefault()
    const curPos = pinToCenter()
    const startX = e.clientX - curPos.x, startY = e.clientY - curPos.y
    const onMove = (ev) => {
      const x = Math.max(0, Math.min(window.innerWidth  - sRef.current.w,  ev.clientX - startX))
      const y = Math.max(0, Math.min(window.innerHeight - sRef.current.h, ev.clientY - startY))
      pRef.current = { x, y }
      setPos({ x, y })
    }
    const onUp = () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [pinToCenter])

  return { size, pos, startResize, startMove }
}

// ── resize handle ─────────────────────────────────────────────────────────
function RH({ cursor, style, onMouseDown }) {
  return (
    <div
      onMouseDown={onMouseDown}
      style={{
        position: 'absolute', zIndex: 20, ...style,
        cursor, userSelect: 'none',
      }}
    />
  )
}

// ── Modal ─────────────────────────────────────────────────────────────────
const EDGE = 6    // px - edge handle thickness
const CORN = 12   // px - corner handle size

export default function Modal({
  title, onClose, children,
  width = 'max-w-2xl',
  maximized = false, onMaximize,
  resizable = false,
  defaultWidth = 900, defaultHeight = 640,
}) {
  const { size, pos, startResize, startMove } = useDragResize(defaultWidth, defaultHeight)

  useEffect(() => {
    const handler = e => { if (e.key === 'Escape') onClose?.() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  if (maximized) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-stretch justify-stretch z-50 p-2">
        <div className="bg-white rounded-lg shadow-2xl w-full h-full flex flex-col">
          <ModalHeader title={title} onClose={onClose} onMaximize={onMaximize} maximized />
          <div className="flex-1 min-h-0 overflow-auto">{children}</div>
        </div>
      </div>
    )
  }

  if (resizable) {
    const { w, h } = size
    const positioned = pos !== null
    const outerStyle = positioned
      ? { position: 'fixed', left: pos.x, top: pos.y, zIndex: 50 }
      : { position: 'fixed', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50, pointerEvents: 'none' }

    return (
      <>
        {/* backdrop */}
        <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />
        <div style={outerStyle}>
          <div
            style={{ width: w, height: h, pointerEvents: 'all', position: 'relative' }}
            className="bg-white rounded-lg shadow-2xl flex flex-col"
          >
            {/* ── resize handles ── */}
            {/* corners */}
            <RH cursor="nwse-resize" onMouseDown={startResize(-1,-1)} style={{ top: 0,    left: 0,  width: CORN, height: CORN }} />
            <RH cursor="nesw-resize" onMouseDown={startResize( 1,-1)} style={{ top: 0,    right: 0, width: CORN, height: CORN }} />
            <RH cursor="nesw-resize" onMouseDown={startResize(-1, 1)} style={{ bottom: 0, left: 0,  width: CORN, height: CORN }} />
            <RH cursor="nwse-resize" onMouseDown={startResize( 1, 1)} style={{ bottom: 0, right: 0, width: CORN, height: CORN }} />
            {/* edges */}
            <RH cursor="ns-resize"  onMouseDown={startResize(0,-1)} style={{ top: 0,    left: CORN, right: CORN, height: EDGE }} />
            <RH cursor="ns-resize"  onMouseDown={startResize(0, 1)} style={{ bottom: 0, left: CORN, right: CORN, height: EDGE }} />
            <RH cursor="ew-resize"  onMouseDown={startResize(-1,0)} style={{ left: 0,   top: CORN, bottom: CORN, width: EDGE }} />
            <RH cursor="ew-resize"  onMouseDown={startResize( 1,0)} style={{ right: 0,  top: CORN, bottom: CORN, width: EDGE }} />

            <ModalHeader title={title} onClose={onClose} onMaximize={onMaximize} onMouseDown={startMove} />
            <div className="flex-1 min-h-0 overflow-auto">{children}</div>

            {/* corner grip icon */}
            <div style={{ position: 'absolute', bottom: 2, right: 4, fontSize: 10, color: '#CBD5E1', pointerEvents: 'none', userSelect: 'none' }}>⊿</div>
          </div>
        </div>
      </>
    )
  }

  // default: centered, no resize
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className={`bg-white rounded-lg shadow-2xl w-full ${width} flex flex-col max-h-[90vh]`}>
        <ModalHeader title={title} onClose={onClose} onMaximize={onMaximize} />
        <div className="flex-1 min-h-0 overflow-auto">{children}</div>
      </div>
    </div>
  )
}

function ModalHeader({ title, onClose, onMaximize, maximized = false, onMouseDown }) {
  return (
    <div
      onMouseDown={onMouseDown}
      className={`flex items-center justify-between px-4 py-3 bg-[#1E3A8A] rounded-t-lg shrink-0 ${onMouseDown ? 'cursor-move select-none' : ''}`}
    >
      <span className="text-white font-semibold">{title}</span>
      <div className="flex items-center gap-2">
        {onMaximize && (
          <button onClick={onMaximize} title={maximized ? 'Restore' : 'Maximize'} className="text-[#93C5FD] hover:text-white text-sm leading-none px-1">
            {maximized ? '⊡' : '⊞'}
          </button>
        )}
        <button onClick={onClose} className="text-[#93C5FD] hover:text-white text-xl leading-none">×</button>
      </div>
    </div>
  )
}
