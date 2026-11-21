import { ErrorBoundary } from './components/ErrorBoundary'
import { ScreenerList } from './components/ScreenerList'
import { StatusBar } from './components/StatusBar'
import { TradingChart } from './components/TradingChart'
import { useScreenerSocket } from './hooks/useScreenerSocket'

export default function App() {
  useScreenerSocket()

  return (
    <div className="flex h-dvh flex-col bg-slate-950 text-slate-200">
      <StatusBar />
      <main className="flex min-h-0 flex-1 flex-col md:flex-row">
        <div className="flex h-72 min-h-0 md:h-auto">
          <ScreenerList />
        </div>
        <ErrorBoundary>
          <TradingChart />
        </ErrorBoundary>
      </main>
    </div>
  )
}
