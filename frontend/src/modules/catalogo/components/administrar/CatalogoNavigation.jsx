import { useLayoutEffect, useRef, useState } from 'react'
import styles from '../../pages/AdministrarCatalogoPage.module.css'

const point = rect => ({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 })

export default function CatalogoNavigation({ tabs, value, onChange }) {
  const track = useRef(null)
  const buttons = useRef(new Map())
  const ghosts = useRef(new Map())
  const [movement, setMovement] = useState(null)
  const index = Math.max(0, tabs.findIndex(t => t.value === value))
  const ordered = [...tabs.slice(index), ...tabs.slice(0, index)]

  useLayoutEffect(() => {
    if (!movement) return
    const animations = []
    const origin = track.current.getBoundingClientRect()
    const slots = ordered.map(t => buttons.current.get(t.value).getBoundingClientRect())
    const compact = Math.abs(slots[0].top - slots[1].top) > 1
    const framesFor = (item, oldIndex) => {
      const targetIndex = (oldIndex - movement.shift + tabs.length) % tabs.length
      const target = slots[targetIndex]
      const frame = (rect, offset, opacity = 1) => ({
        transform: `translate(${rect.left - origin.left}px, ${rect.top - origin.top}px)`,
        width: `${rect.width}px`, height: `${rect.height}px`, opacity, offset,
      })
      if (compact && tabs.length === 4) {
        // Los centros recorren el óvalo en sentido horario: arriba → derecha → abajo → izquierda.
        const centers = slots.map(point)
        const cx = (centers[1].x + centers[3].x) / 2
        const cy = (centers[0].y + centers[2].y) / 2
        const rx = (centers[1].x - centers[3].x) / 2
        const ry = (centers[2].y - centers[0].y) / 2
        const steps = 4 - movement.shift
        const frames = [frame(item.rect, 0)]
        for (let sample = 1; sample <= steps * 8; sample++) {
          const progress = sample / 8
          const start = (oldIndex + Math.floor(progress)) % 4
          const end = (start + 1) % 4
          const fraction = progress % 1
          const width = slots[start].width + (slots[end].width - slots[start].width) * fraction
          const height = slots[start].height + (slots[end].height - slots[start].height) * fraction
          const angle = (-90 + (oldIndex + progress) * 90) * Math.PI / 180
          frames.push(frame({ left: cx + rx * Math.cos(angle) - width / 2,
            top: cy + ry * Math.sin(angle) - height / 2, width, height }, sample / (steps * 8)))
        }
        frames[frames.length - 1] = frame(target, 1)
        return frames
      }
      if (oldIndex >= movement.shift) return [frame(item.rect, 0), frame(target, 1)]
      // En escritorio las opciones que salen por la izquierda vuelven por la derecha.
      const crossing = Math.min(.85, Math.max(.15, (oldIndex + 1) / (movement.shift + 1)))
      return [frame(item.rect, 0),
        frame({ ...item.rect, left: origin.left - item.rect.width }, crossing - .01, 0),
        frame({ ...target, left: origin.right }, crossing + .01, 0), frame(target, 1)]
    }
    for (const [oldIndex, item] of movement.items.entries()) {
      const ghost = ghosts.current.get(item.tab.value)
      animations.push(ghost.animate(framesFor(item, oldIndex), {
        duration: compact ? Math.max(900, (4 - movement.shift) * 450) : 1000,
        easing: 'cubic-bezier(.45,0,.55,1)', fill: 'both',
      }))
    }
    const finish = () => {
      for (const animation of animations) { animation.onfinish = null; animation.cancel() }
      setMovement(null)
      buttons.current.get(value)?.focus({ preventScroll: true })
    }
    animations[0].onfinish = finish
    window.addEventListener('resize', finish, { once: true })
    return () => {
      window.removeEventListener('resize', finish)
      for (const animation of animations) { animation.onfinish = null; animation.cancel() }
    }
  }, [value, movement])

  function select(next) {
    if (next === value || movement) return
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    const items = ordered.map(tab => {
      const rect = buttons.current.get(tab.value).getBoundingClientRect()
      return { tab, rect: { left: rect.left, top: rect.top, width: rect.width, height: rect.height } }
    })
    if (!reduceMotion && track.current?.animate && items[0].rect.width) {
      setMovement({ items, shift: ordered.findIndex(t => t.value === next) })
    }
    onChange(next)
  }

  return <nav className={`${styles.tabs} ${styles.navigationTabs}`}
    aria-label="Secciones del catálogo" aria-busy={Boolean(movement)}>
    <div ref={track} className={styles.navigationTrack}>
      {ordered.map(t => <button key={t.value} type="button"
        ref={button => { if (button) buttons.current.set(t.value, button); else buttons.current.delete(t.value) }}
        className={`${styles.tab} ${value === t.value ? styles.tabActive : ''}`}
        aria-pressed={value === t.value} aria-disabled={movement ? true : undefined}
        onClick={() => select(t.value)}>
        <i className={`ti ${t.icon}`} aria-hidden="true" />{t.label}
      </button>)}
      {movement && <div className={styles.navigationGhostLayer} aria-hidden="true">
        {movement.items.map(({ tab }) => <span key={tab.value}
          ref={node => { if (node) ghosts.current.set(tab.value, node); else ghosts.current.delete(tab.value) }}
          className={`${styles.tab} ${value === tab.value ? styles.tabActive : ''}`}>
          <i className={`ti ${tab.icon}`} />{tab.label}
        </span>)}
      </div>}
    </div>
  </nav>
}
