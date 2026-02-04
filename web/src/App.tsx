import { useState, useEffect } from 'react'
import axios from 'axios'
import { Monitor, Download, ChevronDown, ChevronUp, Loader2, AlertCircle, CheckCircle, Search, SunMoon, Lightbulb } from 'lucide-react'

// Types
interface CaptureRequest {
  url: string
  full_page: boolean
  device: string
  width?: number
  height?: number
  delay: number
  click?: string
  hide?: string
  grab_html: boolean
}

interface CaptureResult {
  screenshot: string
  network_logs: NetworkLog[]
  dom_elements: DOMElements
  final_url: string
  html_source?: string
  session_id: string
}

interface NetworkLog {
  url: string
  method: string
  type: string
  status?: number
  status_text?: string
}

interface DOMElements {
  clickable_elements: any[]
  hidden_elements?: any[]
  forms: any[]
  scripts: any[]
  popups: any[]
  redirect?: string
  title?: string
  url?: string
}

function App() {
  // State
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem('darkMode') === 'true'
  })

  const [formData, setFormData] = useState<CaptureRequest>({
    url: '',
    full_page: false,
    device: 'desktop',
    width: undefined,
    height: undefined,
    delay: 0,
    click: '',
    hide: '',
    grab_html: false
  })

  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<CaptureResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  // State pour tables pliables
  const [showNetwork, setShowNetwork] = useState(false)
  const [showDOM, setShowDOM] = useState(false)
  const [showHTML, setShowHTML] = useState(false)
  const [showClickable, setShowClickable] = useState(false)
  const [showHidden, setShowHidden] = useState(false)
  const [showForms, setShowForms] = useState(false)
  const [showPopups, setShowPopups] = useState(false)
  const [showInlineScripts, setShowInlineScripts] = useState(false)
  const [showExternalScripts, setShowExternalScripts] = useState(false)

  // State pour recherche/filtrage
  const [networkSearch, setNetworkSearch] = useState('')
  const [scriptsSearch, setScriptsSearch] = useState('')
  const [htmlSearch, setHtmlSearch] = useState('')
  const [domSearch, setDomSearch] = useState('')
  const [showScripts, setShowScripts] = useState(false)
  const [showScreenshot, setShowScreenshot] = useState(true)

  // State pour tri des tableaux
  const [networkSort, setNetworkSort] = useState<{column: string, direction: 'asc' | 'desc'} | null>(null)

  // Dark mode effect
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem('darkMode', darkMode.toString())
  }, [darkMode])

  // Fonction pour parser la recherche (inclusions et exclusions)
  const parseSearch = (searchText: string) => {
    if (!searchText) return { include: [], exclude: [] }

    const terms = searchText.split('|').map(t => t.trim()).filter(t => t)
    const include: string[] = []
    const exclude: string[] = []

    terms.forEach(term => {
      if (term.startsWith('!')) {
        exclude.push(term.substring(1))
      } else {
        include.push(term)
      }
    })

    return { include, exclude }
  }

  // Fonction pour verifier si un texte match les criteres de recherche
  const matchesSearch = (text: string, searchText: string): boolean => {
    if (!searchText) return true

    const textStr = String(text || '')
    const textLower = textStr.toLowerCase()

    const { include, exclude } = parseSearch(searchText)

    // Verifier les exclusions (si match une exclusion, rejeter)
    for (const exc of exclude) {
      const excLower = exc.toLowerCase()
      if (textLower.includes(excLower) || textStr.includes(exc)) {
        return false
      }
    }

    // Si pas d'inclusions, accepter (seulement des exclusions)
    if (include.length === 0) return true

    // Verifier les inclusions (doit matcher au moins une)
    for (const inc of include) {
      const incLower = inc.toLowerCase()
      if (textLower.includes(incLower) || textStr.includes(inc)) {
        return true
      }
    }

    return false
  }

  // Fonction pour verifier si un objet match (OR sur tous les champs)
  const matchesSearchAny = (fields: string[], searchText: string): boolean => {
    if (!searchText) return true

    const { include, exclude } = parseSearch(searchText)

    // Verifier les exclusions sur TOUS les champs (si un champ contient l'exclusion, rejeter)
    for (const field of fields) {
      const fieldStr = String(field || '')
      const fieldLower = fieldStr.toLowerCase()

      for (const exc of exclude) {
        const excLower = exc.toLowerCase()
        if (fieldLower.includes(excLower) || fieldStr.includes(exc)) {
          return false  // Rejeter si trouve dans n'importe quel champ
        }
      }
    }

    // Si pas d'inclusions, accepter (seulement des exclusions)
    if (include.length === 0) return true

    // Verifier les inclusions (doit matcher au moins un champ)
    for (const field of fields) {
      const fieldStr = String(field || '')
      const fieldLower = fieldStr.toLowerCase()

      for (const inc of include) {
        const incLower = inc.toLowerCase()
        if (fieldLower.includes(incLower) || fieldStr.includes(inc)) {
          return true  // Accepter si trouve dans n'importe quel champ
        }
      }
    }

    return false
  }

  // Fonction pour surligner le texte de recherche
  const highlightText = (text: string, searchText: string) => {
    if (!searchText || !text) return text

    const { include } = parseSearch(searchText)
    if (include.length === 0) return text

    let result: any[] = [text]

    include.forEach(search => {
      const newResult: any[] = []
      result.forEach(part => {
        if (typeof part === 'string') {
          const lowerPart = part.toLowerCase()
          const lowerSearch = search.toLowerCase()
          let lastIndex = 0
          let index = lowerPart.indexOf(lowerSearch)

          while (index !== -1) {
            if (index > lastIndex) {
              newResult.push(part.substring(lastIndex, index))
            }
            newResult.push(
              <mark key={`${search}-${index}`} className="bg-yellow-300 dark:bg-yellow-600 text-gray-900 dark:text-white px-0.5">
                {part.substring(index, index + search.length)}
              </mark>
            )
            lastIndex = index + search.length
            index = lowerPart.indexOf(lowerSearch, lastIndex)
          }

          if (lastIndex < part.length) {
            newResult.push(part.substring(lastIndex))
          }
        } else {
          newResult.push(part)
        }
      })
      result = newResult
    })

    return result
  }

  // Fonction pour trier un tableau
  const sortData = <T,>(data: T[], column: string, direction: 'asc' | 'desc'): T[] => {
    return [...data].sort((a, b) => {
      let aVal = (a as any)[column]
      let bVal = (b as any)[column]

      // Gerer les valeurs undefined ou null
      if (aVal === undefined || aVal === null) aVal = ''
      if (bVal === undefined || bVal === null) bVal = ''

      // Si c'est un nombre
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return direction === 'asc' ? aVal - bVal : bVal - aVal
      }

      // Convertir en string et comparer
      const aStr = String(aVal).toLowerCase()
      const bStr = String(bVal).toLowerCase()

      // Comparer alphabetiquement
      const comparison = aStr.localeCompare(bStr, undefined, { numeric: true, sensitivity: 'base' })
      return direction === 'asc' ? comparison : -comparison
    })
  }

  // Fonction pour gerer le clic sur un header de colonne
  const handleSort = (
    currentSort: {column: string, direction: 'asc' | 'desc'} | null,
    setSort: (sort: {column: string, direction: 'asc' | 'desc'} | null) => void,
    column: string
  ) => {
    if (currentSort?.column === column) {
      if (currentSort.direction === 'asc') {
        setSort({ column, direction: 'desc' })
      } else {
        setSort(null) // Reset le tri
      }
    } else {
      setSort({ column, direction: 'asc' })
    }
  }

  // Handlers
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const payload = {
        ...formData,
        width: formData.width || undefined,
        height: formData.height || undefined,
        click: formData.click || undefined,
        hide: formData.hide || undefined,
      }

      const response = await axios.post<CaptureResult>('/api/capture', payload)
      setResult(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Erreur lors de la capture')
    } finally {
      setLoading(false)
    }
  }

  const downloadScreenshot = () => {
    if (!result) return

    const link = document.createElement('a')
    link.href = `data:image/png;base64,${result.screenshot}`
    link.download = `screenshot-${Date.now()}.png`
    link.click()
  }

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-gray-50 via-blue-50/30 to-gray-50 dark:from-slate-950 dark:via-indigo-950/50 dark:to-slate-950 transition-colors duration-200">
      {/* Header */}
      <header className="bg-white/80 dark:bg-slate-950/95 backdrop-blur-md shadow-lg border-b border-gray-200/50 dark:border-indigo-900/50 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-blue-600 to-purple-600 rounded-md shadow-lg">
              <Monitor className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Shoturl
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400 font-medium">
                Website Screenshot & Analysis
              </p>
            </div>
          </div>

          <button
            onClick={() => setDarkMode(!darkMode)}
            className="p-3 rounded-md bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 hover:shadow-lg transition-all duration-200 hover:scale-105"
            aria-label="Toggle dark mode"
          >
            {darkMode ? (
              <Lightbulb className="w-5 h-5 text-yellow-400" />
            ) : (
              <SunMoon className="w-5 h-5 text-indigo-600" />
            )}
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 container mx-auto px-4 py-8 flex flex-col justify-center">
        {/* Form */}
        <div className="bg-white/90 dark:bg-slate-950/90 backdrop-blur-sm rounded-md shadow-xl border border-gray-200/50 dark:border-slate-700/50 p-8 mb-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* URL */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Url to capture
              </label>
              <input
                type="text"
                value={formData.url}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                placeholder="https://example.com"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                required
              />
            </div>

            {/* Options en ligne */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Full Page */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.full_page}
                  onChange={(e) => setFormData({ ...formData, full_page: e.target.checked })}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Full Page</span>
              </label>

              {/* Grab HTML */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.grab_html}
                  onChange={(e) => setFormData({ ...formData, grab_html: e.target.checked })}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">HTML Source</span>
              </label>

              {/* Device */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Device
                </label>
                <select
                  value={formData.device}
                  onChange={(e) => setFormData({ ...formData, device: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                >
                  <option value="desktop">Desktop</option>
                  <option value="tablet">Tablet</option>
                  <option value="phone">Phone</option>
                </select>
              </div>
            </div>

            {/* Dimensions */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Width (px)
                </label>
                <input
                  type="number"
                  value={formData.width || ''}
                  onChange={(e) => setFormData({ ...formData, width: e.target.value ? parseInt(e.target.value) : undefined })}
                  placeholder="Auto"
                  min="200"
                  max="3840"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Height (px)
                </label>
                <input
                  type="number"
                  value={formData.height || ''}
                  onChange={(e) => setFormData({ ...formData, height: e.target.value ? parseInt(e.target.value) : undefined })}
                  placeholder="Auto"
                  min="200"
                  max="2160"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Delay (seconds)
                </label>
                <input
                  type="number"
                  value={formData.delay}
                  onChange={(e) => setFormData({ ...formData, delay: parseInt(e.target.value) || 0 })}
                  min="0"
                  max="30"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                />
              </div>
            </div>

            {/* Selectors */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Click Selector (CSS)
                </label>
                <input
                  type="text"
                  value={formData.click}
                  onChange={(e) => setFormData({ ...formData, click: e.target.value })}
                  placeholder=".accept-button"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Hide Selectors (CSS, comma separated)
                </label>
                <input
                  type="text"
                  value={formData.hide}
                  onChange={(e) => setFormData({ ...formData, hide: e.target.value })}
                  placeholder=".popup, .banner"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !formData.url}
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold py-4 px-6 rounded-md transition-all duration-200 flex items-center justify-center gap-3 shadow-lg hover:shadow-xl hover:scale-[1.02] disabled:hover:scale-100 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Capturing...</span>
                </>
              ) : (
                <span>Capture</span>
              )}
            </button>
          </form>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 border-2 border-red-300 dark:border-red-700 rounded-md p-6 mb-8 flex items-start gap-4 shadow-lg">
            <div className="p-2 bg-red-100 dark:bg-red-900/50 rounded-md">
              <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
            <div className="flex-1">
              <h3 className="font-bold text-red-900 dark:text-red-200 text-lg">Error</h3>
              <p className="text-sm text-red-700 dark:text-red-300 mt-2 leading-relaxed">{error}</p>
            </div>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Screenshot - Pliable */}
            <div className="bg-white/90 dark:bg-slate-950/90 backdrop-blur-sm rounded-md shadow-xl border border-gray-200/50 dark:border-indigo-900/30 overflow-hidden">
              <div className="px-6 py-4 flex items-center justify-between bg-gradient-to-r from-green-50 to-transparent dark:from-green-900/20">
                <button
                  onClick={() => setShowScreenshot(!showScreenshot)}
                  className="flex items-center gap-3 flex-1 text-left"
                >
                  <CheckCircle className="w-6 h-6 text-green-500 flex-shrink-0" />
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                      Screenshot Captured
                    </h2>
                    <p className="text-sm text-gray-600 dark:text-gray-400 font-mono">
                      {result.final_url}
                    </p>
                  </div>
                  {showScreenshot ? (
                    <ChevronUp className="w-5 h-5 text-gray-500 ml-auto" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-gray-500 ml-auto" />
                  )}
                </button>
                <button
                  onClick={downloadScreenshot}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md transition-colors ml-4"
                >
                  <Download className="w-4 h-4" />
                  Download
                </button>
              </div>

              {showScreenshot && (
                <div className="p-6 border-t border-gray-200 dark:border-gray-700">
                  <div className="border-2 border-gray-300 dark:border-gray-600 rounded-md overflow-hidden shadow-lg">
                    <img
                      src={`data:image/png;base64,${result.screenshot}`}
                      alt="Screenshot"
                      className="w-full h-auto"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Network Logs - Pliable */}
            <div className="bg-white/90 dark:bg-slate-950/90 backdrop-blur-sm rounded-md shadow-xl border border-gray-200/50 dark:border-indigo-900/30 overflow-hidden">
              <button
                onClick={() => setShowNetwork(!showNetwork)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                  Network Logs ({result.network_logs.filter(log =>
                    matchesSearchAny([log.url, log.method, log.type, log.status?.toString() || ''], networkSearch)
                  ).length} / {result.network_logs.length})
                </h2>
                {showNetwork ? (
                  <ChevronUp className="w-5 h-5 text-gray-500" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-gray-500" />
                )}
              </button>

              {showNetwork && (
                <div className="p-6 border-t border-gray-200 dark:border-gray-700">
                  {/* Search bar */}
                  <div className="mb-4">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="text"
                        value={networkSearch}
                        onChange={(e) => setNetworkSearch(e.target.value)}
                        placeholder="Search: term1 | term2 | !exclude"
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      />
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Use | to separate terms, ! to exclude (e.g., "error | 200 | !image")
                    </p>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200 dark:border-gray-700">
                          <th
                            className="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 select-none"
                            onClick={() => handleSort(networkSort, setNetworkSort, 'status')}
                          >
                            Status {networkSort?.column === 'status' && (networkSort.direction === 'asc' ? '' : '')}
                          </th>
                          <th
                            className="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 select-none"
                            onClick={() => handleSort(networkSort, setNetworkSort, 'method')}
                          >
                            Method {networkSort?.column === 'method' && (networkSort.direction === 'asc' ? '' : '')}
                          </th>
                          <th
                            className="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 select-none"
                            onClick={() => handleSort(networkSort, setNetworkSort, 'type')}
                          >
                            Type {networkSort?.column === 'type' && (networkSort.direction === 'asc' ? '' : '')}
                          </th>
                          <th
                            className="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 select-none"
                            onClick={() => handleSort(networkSort, setNetworkSort, 'url')}
                          >
                            URL {networkSort?.column === 'url' && (networkSort.direction === 'asc' ? '' : '')}
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {(networkSort
                          ? sortData(
                              result.network_logs.filter(log =>
                                matchesSearchAny([log.url, log.method, log.type, log.status?.toString() || ''], networkSearch)
                              ),
                              networkSort.column,
                              networkSort.direction
                            )
                          : result.network_logs.filter(log =>
                              matchesSearchAny([log.url, log.method, log.type, log.status?.toString() || ''], networkSearch)
                            )
                        ).map((log, idx) => (
                          <tr key={idx} className="border-b border-gray-100 dark:border-indigo-900/30">
                            <td className="py-2 px-3">
                              <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                                log.status && log.status < 300 ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300' :
                                log.status && log.status < 400 ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300' :
                                log.status && log.status < 500 ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300' :
                                'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'
                              }`}>
                                {log.status || ''}
                              </span>
                            </td>
                            <td className="py-2 px-3 font-mono text-gray-900 dark:text-gray-100">
                              {networkSearch ? highlightText(log.method, networkSearch) : log.method}
                            </td>
                            <td className="py-2 px-3 text-gray-600 dark:text-gray-400">
                              {networkSearch ? highlightText(log.type, networkSearch) : log.type}
                            </td>
                            <td className="py-2 px-3 text-gray-600 dark:text-gray-400 break-all" title={log.url}>
                              {networkSearch ? highlightText(log.url, networkSearch) : log.url}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            {/* DOM Elements - Pliable */}
            <div className="bg-white/90 dark:bg-slate-950/90 backdrop-blur-sm rounded-md shadow-xl border border-gray-200/50 dark:border-indigo-900/30 overflow-hidden">
              <button
                onClick={() => setShowDOM(!showDOM)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                  DOM Elements ({(result.dom_elements.clickable_elements?.length || 0) + (result.dom_elements.hidden_elements?.length || 0) + (result.dom_elements.forms?.length || 0) + (result.dom_elements.popups?.length || 0)})
                  <span className="text-sm font-normal text-gray-600 dark:text-gray-400 ml-2">
                    ({result.dom_elements.clickable_elements?.length || 0} clickable, {result.dom_elements.hidden_elements?.length || 0} hidden, {result.dom_elements.forms?.length || 0} forms, {result.dom_elements.popups?.length || 0} popups)
                  </span>
                </h2>
                {showDOM ? (
                  <ChevronUp className="w-5 h-5 text-gray-500" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-gray-500" />
                )}
              </button>

              {showDOM && (
                <div className="p-6 border-t border-gray-200 dark:border-gray-700 space-y-4">
                  {/* Search */}
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      value={domSearch}
                      onChange={(e) => setDomSearch(e.target.value)}
                      placeholder="Search in DOM elements..."
                      className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>

                  {/* Clickable Elements - Collapsible */}
                  <div className="border border-gray-200 dark:border-gray-700 rounded-md">
                    <button
                      onClick={() => setShowClickable(!showClickable)}
                      className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    >
                      <h3 className="font-medium text-gray-900 dark:text-white">
                        Clickable Elements ({result.dom_elements.clickable_elements.filter(el =>
                          matchesSearchAny([el.text || '', el.id || '', el.classes || '', el.selector || '', el.tag || ''], domSearch)
                        ).length})
                      </h3>
                      {showClickable ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                    {showClickable && (
                      <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-1 max-h-60 overflow-y-auto">
                        {result.dom_elements.clickable_elements
                          .filter(el =>
                            matchesSearchAny([el.text || '', el.id || '', el.classes || '', el.selector || '', el.tag || ''], domSearch)
                          )
                          .map((el, idx) => {
                            const displayText = el.text || el.id || el.classes || '(no identifier)'
                            return (
                              <div key={idx} className="text-xs bg-gray-50 dark:bg-gray-700/50 p-2 rounded">
                                <div className="flex items-start gap-2 mb-1">
                                  <span className="font-mono text-blue-600 dark:text-blue-400 font-semibold">
                                    {domSearch ? highlightText(el.selector || el.tag, domSearch) : (el.selector || el.tag)}
                                  </span>
                                </div>
                                <div className="text-gray-600 dark:text-gray-400">
                                  {domSearch ? highlightText(displayText, domSearch) : displayText}
                                </div>
                              </div>
                            )
                          })}
                      </div>
                    )}
                  </div>

                  {/* Hidden Elements - Collapsible */}
                  {result.dom_elements.hidden_elements && result.dom_elements.hidden_elements.length > 0 && (
                    <div className="border border-gray-200 dark:border-gray-700 rounded-md">
                      <button
                        onClick={() => setShowHidden(!showHidden)}
                        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                      >
                        <h3 className="font-medium text-gray-900 dark:text-white">
                          Hidden Elements ({result.dom_elements.hidden_elements.filter(el =>
                            matchesSearchAny([el.text || '', el.id || '', el.classes || '', el.selector || '', el.tag || ''], domSearch)
                          ).length})
                        </h3>
                        {showHidden ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                      {showHidden && (
                        <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-1 max-h-60 overflow-y-auto">
                          {result.dom_elements.hidden_elements
                            .filter(el =>
                              matchesSearchAny([el.text || '', el.id || '', el.classes || '', el.selector || '', el.tag || ''], domSearch)
                            )
                            .map((el, idx) => {
                              const displayText = el.text || el.id || el.classes || '(no identifier)'
                              return (
                                <div key={idx} className="text-xs bg-gray-50 dark:bg-gray-700/50 p-2 rounded opacity-60">
                                  <div className="flex items-start gap-2 mb-1">
                                    <span className="font-mono text-gray-500 dark:text-gray-500 font-semibold">
                                      {domSearch ? highlightText(el.selector || el.tag, domSearch) : (el.selector || el.tag)}
                                    </span>
                                  </div>
                                  <div className="text-gray-600 dark:text-gray-400">
                                    {domSearch ? highlightText(displayText, domSearch) : displayText}
                                  </div>
                                </div>
                              )
                            })}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Forms - Collapsible */}
                  {result.dom_elements.forms && result.dom_elements.forms.length > 0 && (
                    <div className="border border-gray-200 dark:border-gray-700 rounded-md">
                      <button
                        onClick={() => setShowForms(!showForms)}
                        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                      >
                        <h3 className="font-medium text-gray-900 dark:text-white">
                          Forms ({result.dom_elements.forms.filter(form =>
                            matchesSearchAny([form.method || '', form.action || '', form.id || ''], domSearch)
                          ).length})
                        </h3>
                        {showForms ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                      {showForms && (
                        <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-2">
                          {result.dom_elements.forms
                            .filter(form =>
                              matchesSearchAny([form.method || '', form.action || '', form.id || ''], domSearch)
                            )
                            .map((form, idx) => (
                            <div key={idx} className="text-sm bg-gray-50 dark:bg-gray-700/50 p-3 rounded">
                              <p className="text-gray-900 dark:text-white font-medium mb-2">
                                {domSearch ? (
                                  <>{highlightText(form.method, domSearch)} {highlightText(form.action || '(no action)', domSearch)}</>
                                ) : (
                                  <>{form.method} {form.action || '(no action)'}</>
                                )}
                              </p>
                              {form.inputs && form.inputs.length > 0 && (
                                <div className="mt-2 space-y-1">
                                  <p className="text-xs text-gray-600 dark:text-gray-400 font-semibold">Inputs:</p>
                                  {form.inputs.map((input: any, inputIdx: number) => (
                                    <div key={inputIdx} className="text-xs text-gray-600 dark:text-gray-400 ml-2">
                                       {input.type} {input.name && `(${input.name})`} {input.required && <span className="text-red-500">*</span>}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Popups/Cookie Banners - Collapsible */}
                  {result.dom_elements.popups && result.dom_elements.popups.length > 0 && (
                    <div className="border border-gray-200 dark:border-gray-700 rounded-md">
                      <button
                        onClick={() => setShowPopups(!showPopups)}
                        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                      >
                        <h3 className="font-medium text-gray-900 dark:text-white">
                          Popups/Modals/Cookie Banners ({result.dom_elements.popups.filter((popup: any) => {
                            const fields = [popup.id || '', popup.classes || '', popup.text || '', ...(popup.buttons || [])]
                            return matchesSearchAny(fields, domSearch)
                          }).length})
                        </h3>
                        {showPopups ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                      {showPopups && (
                        <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-2 max-h-60 overflow-y-auto">
                          {result.dom_elements.popups
                            .filter((popup: any) => {
                              const fields = [popup.id || '', popup.classes || '', popup.text || '', ...(popup.buttons || [])]
                              return matchesSearchAny(fields, domSearch)
                            })
                            .map((popup: any, idx: number) => (
                          <div key={idx} className="text-sm bg-gray-50 dark:bg-gray-700/50 p-3 rounded">
                            <div className="flex items-start gap-2 mb-2">
                              <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium flex-shrink-0 ${
                                popup.visible ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300' : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
                              }`}>
                                {popup.visible ? 'Visible' : 'Hidden'}
                              </span>
                              <span className="font-mono text-gray-900 dark:text-white text-xs break-all">
                                {popup.id || popup.classes || '(no identifier)'}
                              </span>
                            </div>
                            {popup.buttons && popup.buttons.length > 0 && (
                              <div className="mt-2">
                                <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Buttons:</p>
                                <div className="flex flex-wrap gap-1">
                                  {popup.buttons.map((btn: string, btnIdx: number) => (
                                    <span key={btnIdx} className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 rounded">
                                      {btn}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {popup.text && (
                              <p className="text-xs text-gray-600 dark:text-gray-400 mt-2 pl-2 border-l-2 border-gray-300 dark:border-gray-600 line-clamp-3">
                                {popup.text}
                              </p>
                            )}
                          </div>
                        ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Scripts - Pliable */}
            <div className="bg-white/90 dark:bg-slate-950/90 backdrop-blur-sm rounded-md shadow-xl border border-gray-200/50 dark:border-indigo-900/30 overflow-hidden">
              <button
                onClick={() => setShowScripts(!showScripts)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                  Scripts ({result.dom_elements.scripts.filter(s =>
                    matchesSearchAny([s.src || '', s.type || '', s.content || ''], scriptsSearch)
                  ).length} / {result.dom_elements.scripts.length})
                  <span className="text-sm font-normal text-gray-600 dark:text-gray-400 ml-2">
                    ({result.dom_elements.scripts.filter(s => s.src).length} external, {result.dom_elements.scripts.filter(s => s.inline).length} inline)
                  </span>
                </h2>
                {showScripts ? (
                  <ChevronUp className="w-5 h-5 text-gray-500" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-gray-500" />
                )}
              </button>

              {showScripts && (
                <div className="p-6 border-t border-gray-200 dark:border-gray-700">
                  {/* Search bar */}
                  <div className="mb-4 relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      value={scriptsSearch}
                      onChange={(e) => setScriptsSearch(e.target.value)}
                      placeholder="Search in scripts (URL, type)..."
                      className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>

                  <div className="space-y-4">
                    {/* External Scripts - Collapsible */}
                    <div className="border border-gray-200 dark:border-gray-700 rounded-md">
                      <button
                        onClick={() => setShowExternalScripts(!showExternalScripts)}
                        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                      >
                        <h3 className="font-medium text-gray-900 dark:text-white">
                          External Scripts ({result.dom_elements.scripts.filter(s =>
                            s.src &&
                            matchesSearchAny([s.src || '', s.type || ''], scriptsSearch)
                          ).length})
                        </h3>
                        {showExternalScripts ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                      {showExternalScripts && (
                        <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-2 max-h-96 overflow-y-auto">
                          {result.dom_elements.scripts
                            .filter(s =>
                              s.src &&
                              matchesSearchAny([s.src || '', s.type || ''], scriptsSearch)
                            )
                            .map((script, idx) => (
                            <div key={idx} className="bg-gray-50 dark:bg-gray-700/50 p-3 rounded border border-gray-200 dark:border-gray-600">
                              <p className="text-sm text-gray-900 dark:text-white font-mono break-all">
                                {scriptsSearch ? highlightText(script.src, scriptsSearch) : script.src}
                              </p>
                              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                {script.type}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Inline Scripts - Collapsible */}
                    <div className="border border-gray-200 dark:border-gray-700 rounded-md">
                      <button
                        onClick={() => setShowInlineScripts(!showInlineScripts)}
                        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                      >
                        <h3 className="font-medium text-gray-900 dark:text-white">
                          Inline Scripts ({result.dom_elements.scripts.filter(s =>
                            s.inline &&
                            matchesSearchAny([s.type || '', s.content || ''], scriptsSearch)
                          ).length})
                        </h3>
                        {showInlineScripts ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                      {showInlineScripts && (
                        <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-2 max-h-96 overflow-y-auto">
                          {result.dom_elements.scripts
                            .filter(s =>
                              s.inline &&
                              matchesSearchAny([s.type || '', s.content || ''], scriptsSearch)
                            )
                            .map((script, idx) => (
                            <div key={idx} className="bg-gray-50 dark:bg-gray-700/50 p-3 rounded border border-gray-200 dark:border-gray-600">
                              <p className="text-sm text-gray-600 dark:text-gray-400 font-semibold mb-2">
                                Inline script ({scriptsSearch ? highlightText(script.type, scriptsSearch) : script.type})
                              </p>
                              {script.content && (
                                <pre className="text-xs bg-gray-900 dark:bg-black text-green-400 p-3 rounded overflow-x-auto max-h-64">
                                  <code>
                                    {scriptsSearch ? highlightText(script.content, scriptsSearch) : script.content}
                                  </code>
                                </pre>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* HTML Source - Pliable (si grab_html) */}
            {result.html_source && (
              <div className="bg-white/90 dark:bg-slate-950/90 backdrop-blur-sm rounded-md shadow-xl border border-gray-200/50 dark:border-indigo-900/30 overflow-hidden">
                <button
                  onClick={() => setShowHTML(!showHTML)}
                  className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                    HTML Source
                  </h2>
                  {showHTML ? (
                    <ChevronUp className="w-5 h-5 text-gray-500" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-gray-500" />
                  )}
                </button>

                {showHTML && (
                  <div className="p-6 border-t border-gray-200 dark:border-gray-700">
                    {/* Search bar */}
                    <div className="mb-4 flex gap-3">
                      <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                          type="text"
                          value={htmlSearch}
                          onChange={(e) => setHtmlSearch(e.target.value)}
                          placeholder="Search in HTML source..."
                          className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        />
                      </div>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(result.html_source || '')
                          alert('HTML copied to clipboard!')
                        }}
                        className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-md transition-colors text-sm flex items-center gap-2"
                      >
                        <Download className="w-4 h-4" />
                        Copy
                      </button>
                    </div>

                    <div className="border border-gray-300 dark:border-gray-600 rounded-md overflow-hidden">
                      <div className="bg-gray-900 dark:bg-black overflow-x-auto max-h-96">
                        <table className="w-full text-xs font-mono">
                          <tbody>
                            {result.html_source.split('\n').map((line, idx) => {
                              const lineNum = idx + 1
                              const lineMatches = matchesSearch(line, htmlSearch)

                              if (htmlSearch && !lineMatches) return null

                              return (
                                <tr key={idx}>
                                  <td className="px-3 py-1 text-gray-500 dark:text-gray-600 text-right select-none border-r border-gray-700 bg-gray-800/50 dark:bg-gray-950/50" style={{minWidth: '3rem'}}>
                                    {lineNum}
                                  </td>
                                  <td className="px-3 py-1 text-gray-300 dark:text-gray-400">
                                    <code>
                                      {htmlSearch ? highlightText(line, htmlSearch) : line || ' '}
                                    </code>
                                  </td>
                                </tr>
                              )
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {htmlSearch && (
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-2 italic">
                        Showing {result.html_source.split('\n').filter(line =>
                          matchesSearch(line, htmlSearch)
                        ).length} lines matching "{htmlSearch}"
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-auto bg-white/80 dark:bg-slate-900/95 backdrop-blur-md border-t border-gray-200/50 dark:border-indigo-900/30">
        <div className="container mx-auto px-4 py-6 text-center">
          <p className="text-sm text-gray-600 dark:text-gray-400 font-medium">
            Shoturl - Optimized for 4GB RAM with Playwright
          </p>
          <div className="mt-3 flex items-center justify-center gap-4">
            <a
              href="/api/docs"
              className="text-sm px-4 py-2 rounded-md bg-gradient-to-r from-blue-600/10 to-purple-600/10 text-blue-600 dark:text-blue-400 hover:from-blue-600/20 hover:to-purple-600/20 transition-all font-medium"
            >
              API Docs
            </a>
            <a
              href="/api/health"
              className="text-sm px-4 py-2 rounded-md bg-gradient-to-r from-green-600/10 to-emerald-600/10 text-green-600 dark:text-green-400 hover:from-green-600/20 hover:to-emerald-600/20 transition-all font-medium"
            >
              Health Check
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
