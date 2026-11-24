import { useEffect } from 'react'
import { fetchScreener, isAbortError } from '../services/api'
import { ScreenerSocket } from '../services/ws'
import { useScreenerStore } from '../store'

/** Connects the screener WebSocket for the component's lifetime and loads the initial REST snapshot. */
export function useScreenerSocket() {
  useEffect(() => {
    const socket = new ScreenerSocket()
    socket.connect()

    const controller = new AbortController()
    fetchScreener(controller.signal)
      .then((snap) => useScreenerStore.getState().setSnapshot(snap))
      .catch((err) => {
        if (isAbortError(err)) return
        // 503 before the first scan is expected; the WS push will deliver data.
        const message = err instanceof Error ? err.message : 'Failed to load screener'
        useScreenerStore.getState().setScanError(message)
      })

    return () => {
      controller.abort()
      socket.disconnect()
    }
  }, [])
}
