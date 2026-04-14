import { useEffect, useMemo, useRef, useState } from 'react'

const QUESTION_BANK_URL = '/demo_questions.json'
const PHOTO_CANDIDATES = ['/profile-photo.png', '/profile-photo.jpg', '/profile-photo.jpeg']
const DEFAULT_ANSWER_API_URL = '/api/answer'
const PDF_VIEWER_FRAGMENT = '#toolbar=1&navpanes=1&scrollbar=1&view=FitH'

const REPORTS = [
  {
    id: 'volkswagen_2024',
    company: 'Volkswagen Group',
    file: 'volkswagen_2024.pdf',
  },
  {
    id: 'mercedes_2024',
    company: 'Mercedes-Benz Group',
    file: 'mercedes_2024.pdf',
  },
  {
    id: 'bmw_2024',
    company: 'BMW Group',
    file: 'bmw_2024.pdf',
  },
  {
    id: 'siemens_2024',
    company: 'Siemens AG',
    file: 'siemens_2024.pdf',
  },
  {
    id: 'bosch_2024',
    company: 'Robert Bosch GmbH',
    file: 'bosch_2024.pdf',
  },
]

const starterMessage = {
  id: 'welcome',
  role: 'assistant',
  content:
    'Hi. Ask me anything about annual reports of Volkswagen, BMW, Mercedes-Benz, Siemens, and Bosch.',
  meta: 'Grounded responses only',
}

function stripTrailingSlashes(value) {
  return typeof value === 'string' ? value.replace(/\/+$/, '') : ''
}

function resolveAnswerApiUrl() {
  const configuredAnswerUrl = extractText(import.meta.env.VITE_ANSWER_API_URL)
  if (configuredAnswerUrl) {
    return configuredAnswerUrl
  }

  const configuredApiBaseUrl = extractText(import.meta.env.VITE_API_BASE_URL)
  if (configuredApiBaseUrl) {
    return `${stripTrailingSlashes(configuredApiBaseUrl)}/api/answer`
  }

  return DEFAULT_ANSWER_API_URL
}

function resolveApiBaseUrl(answerApiUrl) {
  const sanitizedAnswerUrl =
    typeof answerApiUrl === 'string' ? answerApiUrl.split('#')[0].split('?')[0] : ''
  if (!sanitizedAnswerUrl) {
    return ''
  }

  const basePath = stripTrailingSlashes(sanitizedAnswerUrl.replace(/\/api\/answer\/?$/, ''))
  if (!basePath) {
    return ''
  }

  if (basePath.startsWith('/')) {
    return basePath
  }

  try {
    const resolvedUrl = new URL(basePath)
    resolvedUrl.hash = ''
    resolvedUrl.search = ''
    resolvedUrl.pathname = stripTrailingSlashes(resolvedUrl.pathname)
    return stripTrailingSlashes(resolvedUrl.toString())
  } catch {
    return ''
  }
}

function buildReportUrl(apiBaseUrl, fileName) {
  const relativePath = `/reports/${encodeURIComponent(fileName)}`
  if (!apiBaseUrl) {
    return relativePath
  }

  return `${stripTrailingSlashes(apiBaseUrl)}${relativePath}`
}

function extractText(content) {
  if (!content || typeof content !== 'string') {
    return ''
  }
  return content.trim()
}

function normalizeList(items) {
  return Array.isArray(items) ? items.filter(Boolean) : []
}

function formatResource(resource) {
  if (!resource || typeof resource !== 'object') {
    return ''
  }

  const pieces = [resource.company, resource.source_file || resource.sourceFile]
  const pageValue = resource.page_number ?? resource.pageNumber
  if (pageValue !== undefined && pageValue !== null && pageValue !== '') {
    pieces.push(`p. ${pageValue}`)
  }

  const formatted = pieces.filter(Boolean).join(' | ')
  if (formatted) {
    return formatted
  }

  return extractText(resource.raw || resource.text || resource.content)
}

function formatEvidenceItem(item) {
  if (typeof item === 'string') {
    return item.trim()
  }

  if (!item || typeof item !== 'object') {
    return ''
  }

  const text = extractText(item.text || item.evidence || item.content || item.raw)
  if (!text) {
    return ''
  }

  const sourceParts = [item.company, item.source_file || item.sourceFile]
  const pageValue = item.page_number ?? item.pageNumber
  if (pageValue !== undefined && pageValue !== null && pageValue !== '') {
    sourceParts.push(`p. ${pageValue}`)
  }

  const source = sourceParts.filter(Boolean).join(' | ')
  return source ? `${text}\n${source}` : text
}

export default function App() {
  const [questionBank, setQuestionBank] = useState([])
  const [isLoadingBank, setIsLoadingBank] = useState(true)
  const [bankError, setBankError] = useState('')
  const [messages, setMessages] = useState([starterMessage])
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [photoIndex, setPhotoIndex] = useState(0)
  const transcriptRef = useRef(null)
  const reportsSectionRef = useRef(null)
  const answerApiUrl = useMemo(() => resolveAnswerApiUrl(), [])
  const reportApiBaseUrl = useMemo(() => resolveApiBaseUrl(answerApiUrl), [answerApiUrl])

  useEffect(() => {
    let active = true

    async function loadQuestionBank() {
      try {
        const response = await fetch(QUESTION_BANK_URL)
        if (!response.ok) {
          throw new Error(`Question bank request failed with HTTP ${response.status}`)
        }
        const data = await response.json()
        if (!active) {
          return
        }
        setQuestionBank(Array.isArray(data.categories) ? data.categories : [])
        setBankError('')
      } catch (error) {
        if (!active) {
          return
        }
        setBankError('Example question bank could not be loaded.')
      } finally {
        if (active) {
          setIsLoadingBank(false)
        }
      }
    }

    loadQuestionBank()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
    }
  }, [messages])

  const displayedCategories = useMemo(() => questionBank, [questionBank])

  async function handleSubmit(event) {
    event.preventDefault()
    const question = input.trim()
    if (!question || isSending) {
      return
    }

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: question,
    }

    setMessages((current) => [...current, userMessage])
    setInput('')
    setIsSending(true)

    try {
      const response = await fetch(answerApiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question }),
      })

      if (!response.ok) {
        throw new Error(`API returned HTTP ${response.status}`)
      }

      const payload = await response.json()
      const answerText = extractText(payload.answer) || 'No answer body was returned by the API.'
      const resources = normalizeList(payload.resources)
      const evidence = normalizeList(payload.evidence)

      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: answerText,
          meta: payload.mode || 'Live agent response',
          resources,
          evidence,
        },
      ])
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content:
            'The UI is ready, but the API is not currently reachable. Start the local API service, then this chat box can call the agent directly.',
          meta: 'Waiting for API service',
        },
      ])
    } finally {
      setIsSending(false)
    }
  }

  function handleQuestionPick(question) {
    setInput(question)
  }

  function handleComposerKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      const form = event.currentTarget.form
      if (form) {
        form.requestSubmit()
      }
    }
  }

  function scrollToReports() {
    reportsSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function handlePhotoError() {
    setPhotoIndex((current) => {
      if (current >= PHOTO_CANDIDATES.length) {
        return current
      }
      return current + 1
    })
  }

  const photoSource = PHOTO_CANDIDATES[photoIndex] || '/portrait-placeholder.svg'

  return (
    <div className="app-shell">
      <div className="background-glow background-glow-a" />
      <div className="background-glow background-glow-b" />

      <main className="page-column">
        <section className="hero-stack">
          <div className="hero-title-row">
            <article className="media-slot photo-slot">
              <img src={photoSource} alt="Your portrait" onError={handlePhotoError} />
            </article>

            <div className="hero-copy">
              <h1>Annual Report RAG Agent</h1>
              <p className="subtitle">
                Ask grounded questions about the 2024 annual reports of Volkswagen,
                Mercedes-Benz, BMW, Siemens, and Bosch.
              </p>
            </div>

            <div className="hero-spacer" aria-hidden="true" />
          </div>

          <section className="interaction-row">
            <section className="compact-card chat-card">
              <header className="chat-header">
                <div>
                  <h2>Chat with the Agent</h2>
                  <p>Type a question and press Enter or click Send.</p>
                </div>
                <div className="chat-header-actions">
                  <button type="button" className="reports-link" onClick={scrollToReports}>
                    Here are the annual reports
                  </button>
                </div>
              </header>

              <div className="transcript" ref={transcriptRef}>
                {messages.map((message) => (
                  <article key={message.id} className={`message-bubble message-${message.role}`}>
                    <div className="message-label">
                      <span>{message.role === 'assistant' ? 'Agent' : 'You'}</span>
                      {message.meta ? <small>{message.meta}</small> : null}
                    </div>
                    <p>{message.content}</p>
                    {message.resources?.length || message.evidence?.length ? (
                      <div className="message-actions">
                        {message.resources?.length ? (
                          <details className="message-detail-toggle">
                            <summary>Resources</summary>
                            <div className="message-detail-block">
                              <ul>
                                {message.resources.map((resource, index) => (
                                  <li key={`${message.id}-resource-${index}`}>
                                    {formatResource(resource)}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </details>
                        ) : null}

                        {message.evidence?.length ? (
                          <details className="message-detail-toggle">
                            <summary>Evidence</summary>
                            <div className="message-detail-block">
                              <ul>
                                {message.evidence.map((item, index) => (
                                  <li key={`${message.id}-evidence-${index}`}>
                                    {formatEvidenceItem(item)}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </details>
                        ) : null}
                      </div>
                    ) : null}
                  </article>
                ))}

                {isSending ? (
                  <article className="message-bubble message-assistant pending-bubble">
                    <div className="message-label">
                      <span>Agent</span>
                      <small>Thinking</small>
                    </div>
                    <p>Preparing a grounded answer from the annual reports...</p>
                  </article>
                ) : null}
              </div>

              <form className="composer" onSubmit={handleSubmit}>
                <label className="sr-only" htmlFor="chat-input">
                  Ask the agent a question
                </label>
                <textarea
                  id="chat-input"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={handleComposerKeyDown}
                  placeholder="Ask about revenue, outlook, risks, tables, evidence location, or comparisons..."
                  rows={3}
                />

                <div className="composer-footer">
                  <p>Click a prompt on the right or ask your own question.</p>
                  <button type="submit" disabled={isSending || !input.trim()}>
                    {isSending ? 'Sending...' : 'Send'}
                  </button>
                </div>
              </form>
            </section>

            <section className="compact-card example-card">
              <div className="compact-card-header">
                <div>
                  <h2>Example questions</h2>
                  <p>Scroll to see questions from different categories.</p>
                </div>
              </div>

              <div className="example-scroll">
                {isLoadingBank ? <p className="muted">Loading question bank...</p> : null}
                {bankError ? <p className="muted">{bankError}</p> : null}

                {displayedCategories.map((category) => (
                  <article className="category-block" key={category.category_id}>
                    <header className="category-header">
                      <h3>{category.category_name}</h3>
                    </header>

                <div className="question-list">
                  {(category.cases || []).map((questionCase) => (
                        <button
                          key={questionCase.case_id}
                          type="button"
                          className="question-pill"
                          onClick={() => handleQuestionPick(questionCase.question)}
                        >
                          {questionCase.question}
                        </button>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </section>
        </section>

        <section className="reports-section" id="reports" ref={reportsSectionRef}>
          <div className="reports-intro">
            <h2>Original annual reports</h2>
          </div>

          <div className="reports-grid">
            {REPORTS.map((report) => {
              const reportUrl = buildReportUrl(reportApiBaseUrl, report.file)
              const reportViewerUrl = `${reportUrl}${PDF_VIEWER_FRAGMENT}`

              return (
                <article className="report-card" key={report.id}>
                  <div className="report-card-header">
                    <div>
                      <h3>{report.company}</h3>
                    </div>
                    <div className="report-card-actions">
                      <a href={reportUrl} target="_blank" rel="noreferrer">
                        Open PDF
                      </a>
                      <a href={reportUrl} download>
                        Download PDF
                      </a>
                    </div>
                  </div>

                  <div className="report-frame-shell">
                    <object
                      className="report-frame"
                      data={reportViewerUrl}
                      type="application/pdf"
                      aria-label={`${report.company} annual report`}
                    >
                      <iframe
                        className="report-frame"
                        src={reportViewerUrl}
                        title={`${report.company} annual report`}
                        loading="lazy"
                      />
                    </object>
                  </div>

                  <p className="report-help">
                    If the preview does not load, use Open PDF to view it in a new tab.
                  </p>
                </article>
              )
            })}
          </div>
        </section>
      </main>
    </div>
  )
}
