import { useCallback, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { getInvoiceById, uploadBulk, uploadInvoice } from '../../api/invoices'
import { getFileIconFromName } from '../../components/invoices/FileTypeBadge'
import type { BulkUploadItemResult, InvoiceStatus } from '../../types/invoice'

const ACCEPTED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png']
const ACCEPTED_MIME = ['application/pdf', 'image/jpeg', 'image/png']

function isAcceptedFile(file: File): boolean {
  const ext = `.${file.name.split('.').pop()?.toLowerCase() ?? ''}`
  return ACCEPTED_EXTENSIONS.includes(ext) || ACCEPTED_MIME.includes(file.type)
}

const TERMINAL_STATUSES: InvoiceStatus[] = ['PROCESSED', 'REVIEW_REQUIRED', 'ERROR']

async function waitForOcrCompletion(invoiceId: string): Promise<InvoiceStatus> {
  const maxAttempts = 30
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const invoice = await getInvoiceById(invoiceId)
    if (TERMINAL_STATUSES.includes(invoice.status)) {
      return invoice.status
    }
    await new Promise((resolve) => setTimeout(resolve, 2000))
  }
  return 'PROCESSING'
}

export default function UploadPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const bulkInputRef = useRef<HTMLInputElement>(null)

  const [dragOver, setDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isUploading, setIsUploading] = useState(false)
  const [isProcessingOcr, setIsProcessingOcr] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [bulkResults, setBulkResults] = useState<BulkUploadItemResult[]>([])
  const [isBulkUploading, setIsBulkUploading] = useState(false)

  const handleFile = useCallback((file: File | null) => {
    if (!file) return
    if (!isAcceptedFile(file)) {
      setError('Only PDF, JPG, and PNG files are accepted.')
      return
    }
    setError(null)
    setSelectedFile(file)
  }, [])

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      setDragOver(false)
      handleFile(event.dataTransfer.files[0] ?? null)
    },
    [handleFile],
  )

  const onSingleUpload = async () => {
    if (!selectedFile) return
    setIsUploading(true)
    setUploadProgress(0)
    setError(null)

    try {
      const invoice = await uploadInvoice(selectedFile, setUploadProgress)
      setIsUploading(false)
      setIsProcessingOcr(true)
      await waitForOcrCompletion(invoice.id)
      navigate(`/invoices/${invoice.id}`)
    } catch {
      setError('Upload failed. Please try again.')
      setIsUploading(false)
      setIsProcessingOcr(false)
    }
  }

  const onBulkUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    setIsBulkUploading(true)
    setBulkResults([])
    setError(null)

    try {
      const response = await uploadBulk(files)
      setBulkResults(response.results)
    } catch {
      setError('Bulk upload failed. Please try again.')
    } finally {
      setIsBulkUploading(false)
    }
  }

  return (
    <div className="page-container page-container--wide">
      <div className="page-header">
        <h1>Upload invoices</h1>
        <Link to="/invoices" className="link link--inline">
          View all invoices
        </Link>
      </div>

      {error && <div className="form-error">{error}</div>}

      <section className="upload-section">
        <h2>Single upload</h2>
        <div
          className={`drop-zone${dragOver ? ' drop-zone--active' : ''}`}
          onDragOver={(e) => {
            e.preventDefault()
            setDragOver(true)
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            hidden
            onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
          />
          <p className="drop-zone__title">Drag & drop a file here</p>
          <p className="drop-zone__hint">or click to browse — PDF, JPG, PNG</p>
          {selectedFile && (
            <div className="drop-zone__file">
              <span>{getFileIconFromName(selectedFile.name)}</span>
              <span>{selectedFile.name}</span>
              <span className="drop-zone__size">
                ({Math.max(1, Math.round(selectedFile.size / 1024))} KB)
              </span>
            </div>
          )}
        </div>

        {isUploading && (
          <div className="progress-bar">
            <div className="progress-bar__fill" style={{ width: `${uploadProgress}%` }} />
            <span className="progress-bar__label">Uploading… {uploadProgress}%</span>
          </div>
        )}

        {isProcessingOcr && (
          <div className="ocr-spinner">
            <div className="spinner" />
            <span>Processing OCR…</span>
          </div>
        )}

        <button
          type="button"
          className="btn btn-primary"
          disabled={!selectedFile || isUploading || isProcessingOcr}
          onClick={onSingleUpload}
        >
          Upload invoice
        </button>
      </section>

      <section className="upload-section">
        <h2>Bulk upload</h2>
        <p className="auth-subtitle" style={{ textAlign: 'left' }}>
          Select up to 20 files at once.
        </p>
        <input
          ref={bulkInputRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          multiple
          hidden
          onChange={(e) => onBulkUpload(e.target.files)}
        />
        <button
          type="button"
          className="btn btn-secondary"
          disabled={isBulkUploading}
          onClick={() => bulkInputRef.current?.click()}
        >
          {isBulkUploading ? 'Uploading…' : 'Select multiple files'}
        </button>

        {bulkResults.length > 0 && (
          <ul className="bulk-results">
            {bulkResults.map((result) => (
              <li
                key={result.filename}
                className={`bulk-results__item bulk-results__item--${result.status}`}
              >
                <span>{getFileIconFromName(result.filename)}</span>
                <span className="bulk-results__name">{result.filename}</span>
                {result.status === 'success' && result.invoice_id ? (
                  <Link to={`/invoices/${result.invoice_id}`} className="link link--inline">
                    View
                  </Link>
                ) : (
                  <span className="bulk-results__error">{result.error_message}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
