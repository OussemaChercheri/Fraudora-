import type { FileType } from '../../types/invoice'

const FILE_ICONS: Record<FileType, string> = {
  PDF: '📄',
  JPG: '🖼',
  PNG: '🖼',
}

export default function FileTypeBadge({ fileType }: { fileType: FileType }) {
  return (
    <span className="file-type-badge">
      <span className="file-type-badge__icon" aria-hidden="true">
        {FILE_ICONS[fileType]}
      </span>
      {fileType}
    </span>
  )
}

export function getFileIconFromName(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (ext === 'pdf') return '📄'
  if (ext === 'jpg' || ext === 'jpeg' || ext === 'png') return '🖼'
  return '📎'
}
