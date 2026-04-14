import { useEffect, useMemo, useRef, useState } from 'react'
import { getDocument } from 'pdfjs-dist/webpack.mjs'

function clampPage(pageNumber, pageCount) {
  if (!pageCount) {
    return 1
  }
  return Math.min(Math.max(pageNumber, 1), pageCount)
}

export default function PdfPreview({
  fileUrl,
  title,
  className = '',
  initialPage = 1,
}) {
  const containerRef = useRef(null)
  const canvasRef = useRef(null)
  const loadingTaskRef = useRef(null)
  const renderTaskRef = useRef(null)
  const pdfDocumentRef = useRef(null)

  const [pageCount, setPageCount] = useState(0)
  const [pageNumber, setPageNumber] = useState(initialPage)
  const [pageInput, setPageInput] = useState(String(initialPage))
  const [viewerWidth, setViewerWidth] = useState(0)
  const [docStatus, setDocStatus] = useState('idle')
  const [renderStatus, setRenderStatus] = useState('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const pageInputId = useMemo(
    () => `pdf-page-input-${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
    [title],
  )

  useEffect(() => {
    setPageNumber(initialPage)
    setPageInput(String(initialPage))
  }, [initialPage, fileUrl])

  useEffect(() => {
    if (!containerRef.current) {
      return undefined
    }

    function updateViewerWidth() {
      if (containerRef.current) {
        setViewerWidth(containerRef.current.clientWidth)
      }
    }

    updateViewerWidth()

    let observer
    if (typeof ResizeObserver !== 'undefined') {
      observer = new ResizeObserver(updateViewerWidth)
      observer.observe(containerRef.current)
    } else {
      window.addEventListener('resize', updateViewerWidth)
    }

    return () => {
      observer?.disconnect()
      window.removeEventListener('resize', updateViewerWidth)
    }
  }, [])

  useEffect(() => {
    let isActive = true

    async function cleanupCurrentDocument() {
      if (renderTaskRef.current) {
        try {
          renderTaskRef.current.cancel()
        } catch {
          // Ignore cancelled render cleanups.
        }
        renderTaskRef.current = null
      }

      if (loadingTaskRef.current) {
        try {
          await loadingTaskRef.current.destroy()
        } catch {
          // Ignore loading task cleanup errors.
        }
        loadingTaskRef.current = null
      }

      if (pdfDocumentRef.current) {
        try {
          await pdfDocumentRef.current.destroy()
        } catch {
          // Ignore document cleanup errors.
        }
        pdfDocumentRef.current = null
      }
    }

    async function loadDocument() {
      await cleanupCurrentDocument()

      setDocStatus('loading')
      setRenderStatus('idle')
      setErrorMessage('')
      setPageCount(0)

      const loadingTask = getDocument({
        url: fileUrl,
        disableAutoFetch: false,
        disableRange: false,
        disableStream: false,
        useWorkerFetch: true,
      })
      loadingTaskRef.current = loadingTask

      try {
        const pdfDocument = await loadingTask.promise
        if (!isActive) {
          await pdfDocument.destroy()
          return
        }

        pdfDocumentRef.current = pdfDocument
        setPageCount(pdfDocument.numPages)
        const safePage = clampPage(initialPage, pdfDocument.numPages)
        setPageNumber(safePage)
        setPageInput(String(safePage))
        setDocStatus('ready')
      } catch (error) {
        if (!isActive) {
          return
        }
        setDocStatus('error')
        setRenderStatus('error')
        setErrorMessage('This PDF preview could not be rendered in the app.')
      }
    }

    loadDocument()

    return () => {
      isActive = false
      cleanupCurrentDocument()
    }
  }, [fileUrl, initialPage])

  useEffect(() => {
    const pdfDocument = pdfDocumentRef.current
    const canvas = canvasRef.current
    if (!pdfDocument || !canvas || !viewerWidth || docStatus !== 'ready') {
      return undefined
    }

    let isActive = true

    async function renderPage() {
      setRenderStatus('rendering')
      setErrorMessage('')

      try {
        const page = await pdfDocument.getPage(pageNumber)
        if (!isActive) {
          return
        }

        const baseViewport = page.getViewport({ scale: 1 })
        const availableWidth = Math.max(viewerWidth - 32, 320)
        const scale = Math.max(0.5, availableWidth / baseViewport.width)
        const viewport = page.getViewport({ scale })
        const devicePixelRatio = window.devicePixelRatio || 1
        const context = canvas.getContext('2d')

        canvas.width = Math.floor(viewport.width * devicePixelRatio)
        canvas.height = Math.floor(viewport.height * devicePixelRatio)
        canvas.style.width = `${viewport.width}px`
        canvas.style.height = `${viewport.height}px`

        context.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0)
        context.clearRect(0, 0, viewport.width, viewport.height)

        const renderTask = page.render({
          canvasContext: context,
          viewport,
        })
        renderTaskRef.current = renderTask
        await renderTask.promise

        if (isActive) {
          setRenderStatus('ready')
        }
      } catch (error) {
        if (!isActive || error?.name === 'RenderingCancelledException') {
          return
        }
        setRenderStatus('error')
        setErrorMessage('This PDF page could not be rendered in the app.')
      }
    }

    renderPage()

    return () => {
      isActive = false
      if (renderTaskRef.current) {
        try {
          renderTaskRef.current.cancel()
        } catch {
          // Ignore cancelled render cleanups.
        }
        renderTaskRef.current = null
      }
    }
  }, [docStatus, fileUrl, pageNumber, viewerWidth])

  const isBusy = docStatus === 'loading' || renderStatus === 'rendering'
  const canGoBack = pageNumber > 1
  const canGoForward = pageCount > 0 && pageNumber < pageCount
  const statusLabel = useMemo(() => {
    if (docStatus === 'loading') {
      return 'Loading preview...'
    }
    if (renderStatus === 'rendering') {
      return `Rendering page ${pageNumber}...`
    }
    if (errorMessage) {
      return errorMessage
    }
    return ''
  }, [docStatus, errorMessage, pageNumber, renderStatus])

  function goToPage(nextPage) {
    const safePage = clampPage(nextPage, pageCount)
    setPageNumber(safePage)
    setPageInput(String(safePage))
  }

  function handlePageSubmit(event) {
    event.preventDefault()
    const requestedPage = Number.parseInt(pageInput, 10)
    if (Number.isNaN(requestedPage)) {
      setPageInput(String(pageNumber))
      return
    }
    goToPage(requestedPage)
  }

  return (
    <div className={`pdf-preview ${className}`.trim()}>
      <div className="pdf-toolbar">
        <div className="pdf-toolbar-group">
          <button type="button" onClick={() => goToPage(pageNumber - 1)} disabled={!canGoBack}>
            Previous
          </button>
          <button type="button" onClick={() => goToPage(pageNumber + 1)} disabled={!canGoForward}>
            Next
          </button>
        </div>

        <form className="pdf-page-form" onSubmit={handlePageSubmit}>
          <label className="sr-only" htmlFor={pageInputId}>
            Go to page
          </label>
          <input
            id={pageInputId}
            inputMode="numeric"
            pattern="[0-9]*"
            value={pageInput}
            onChange={(event) => setPageInput(event.target.value)}
            aria-label={`Page number for ${title}`}
          />
          <span>{pageCount ? `of ${pageCount}` : 'of -'}</span>
        </form>
      </div>

      <div className="pdf-canvas-shell" ref={containerRef}>
        <canvas ref={canvasRef} aria-label={`${title} preview`} />
        {statusLabel ? <p className="pdf-status">{statusLabel}</p> : null}
        {isBusy ? <div className="pdf-loading-overlay" aria-hidden="true" /> : null}
      </div>
    </div>
  )
}
