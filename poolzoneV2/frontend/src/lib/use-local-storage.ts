import { useState } from "react"

export function useLocalStorage<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => {
    const raw = localStorage.getItem(key)
    if (raw != null) {
      try {
        return JSON.parse(raw) as T
      } catch {
        /* fall through to initial */
      }
    }
    return initial
  })
  const set = (v: T) => {
    setValue(v)
    localStorage.setItem(key, JSON.stringify(v))
  }
  return [value, set] as const
}
