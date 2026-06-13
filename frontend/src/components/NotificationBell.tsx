import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getNotifications, markAsRead, markAllRead } from '../api/notifications'
import type { NotificationResponse } from '../types/notification'

function notificationTypeIcon(type: string): string {
  if (type === 'DUPLICATE_ALERT') return '\u{1F4C4}' // copy
  if (type === 'ANOMALY_ALERT') return '\u26A0\uFE0F' // warning
  if (type === 'INVOICE_PROCESSED') return '\u2705' // check
  if (type === 'INVOICE_ERROR') return '\u274C' // x
  return '\u2139\uFE0F' // info
}

function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'à l\'instant'
  if (mins < 60) return `il y a ${mins} min`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `il y a ${hours}h`
  const days = Math.floor(hours / 24)
  if (days < 30) return `il y a ${days}j`
  return new Date(dateStr).toLocaleDateString('fr-FR')
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => getNotifications({ page: 1, page_size: 10 }),
    refetchInterval: 10000,
  })

  const markReadMut = useMutation({
    mutationFn: markAsRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })

  const markAllMut = useMutation({
    mutationFn: markAllRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const unreadCount = data?.unread_count ?? 0
  const items = data?.items ?? []

  function handleItemClick(n: NotificationResponse) {
    if (!n.is_read) markReadMut.mutate(n.id)
    setOpen(false)
    if (n.related_invoice_id) navigate(`/invoices/${n.related_invoice_id}`)
  }

  return (
    <div className="notification-bell" ref={ref}>
      <button className="notification-bell__btn" onClick={() => setOpen(!open)}>
        <span className="notification-bell__icon">{'\uD83D\uDD14'}</span>
        {unreadCount > 0 && <span className="notification-bell__badge">{unreadCount}</span>}
      </button>
      {open && (
        <div className="notification-dropdown">
          <div className="notification-dropdown__header">
            <span>Notifications</span>
            {unreadCount > 0 && (
              <button
                className="notification-dropdown__mark-all"
                onClick={() => markAllMut.mutate()}
                disabled={markAllMut.isPending}
              >
                Tout marquer comme lu
              </button>
            )}
          </div>
          <div className="notification-dropdown__list">
            {items.length === 0 ? (
              <div className="notification-dropdown__empty">Aucune notification</div>
            ) : (
              items.map((n) => (
                <div
                  key={n.id}
                  className={`notification-dropdown__item${n.is_read ? '' : ' notification-dropdown__item--unread'}`}
                  onClick={() => handleItemClick(n)}
                >
                  <span className="notification-dropdown__item-icon">
                    {notificationTypeIcon(n.notification_type)}
                  </span>
                  <div className="notification-dropdown__item-body">
                    <div className="notification-dropdown__item-title">{n.title}</div>
                    <div className="notification-dropdown__item-message">
                      {n.message.length > 60 ? n.message.slice(0, 60) + '\u2026' : n.message}
                    </div>
                    <div className="notification-dropdown__item-time">{relativeTime(n.created_at)}</div>
                  </div>
                  {!n.is_read && <span className="notification-dropdown__dot" />}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
