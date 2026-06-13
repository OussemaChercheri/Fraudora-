import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { getThresholds, updateThreshold } from '../../api/settings'

export default function ThresholdsSettingsPage() {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState<Record<string, string>>({})

  const { data: thresholds, isLoading } = useQuery({
    queryKey: ['thresholds'],
    queryFn: getThresholds,
  })

  const updateMut = useMutation({
    mutationFn: ({ key, value }: { key: string; value: number }) => updateThreshold(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['thresholds'] })
      setEditing({})
    },
  })

  function handleValueChange(key: string, raw: string) {
    setEditing((prev) => ({ ...prev, [key]: raw }))
  }

  function handleSave(key: string, currentValue: number) {
    const raw = editing[key]
    if (raw === undefined || raw === '') return
    const num = parseFloat(raw)
    if (isNaN(num)) return
    updateMut.mutate({ key, value: num })
  }

  if (isLoading) return (
    <div className="page-container">
      <h1>Seuils d'alerte</h1>
      <p>Chargement...</p>
    </div>
  )

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Seuils d'alerte</h1>
      </div>
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Description</th>
              <th>Valeur actuelle</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {thresholds?.map((t) => {
              const isDailyEmail = t.threshold_key === 'daily_email_enabled'
              const editValue = editing[t.threshold_key] ?? String(t.threshold_value)
              const isDirty = parseFloat(editValue) !== t.threshold_value

              return (
                <tr key={t.id}>
                  <td>{t.description}</td>
                  <td>
                    {isDailyEmail ? (
                      <label className="toggle-switch">
                        <input
                          type="checkbox"
                          checked={parseFloat(editValue) === 1}
                          onChange={() => handleValueChange(t.threshold_key, parseFloat(editValue) === 1 ? '0' : '1')}
                        />
                        <span className="toggle-slider" />
                        <span style={{ marginLeft: 8, fontSize: 14 }}>
                          {parseFloat(editValue) === 1 ? 'Activé' : 'Désactivé'}
                        </span>
                      </label>
                    ) : (
                      <input
                        type="number"
                        step="any"
                        className="threshold-input"
                        value={editValue}
                        onChange={(e) => handleValueChange(t.threshold_key, e.target.value)}
                        style={{ width: 120 }}
                      />
                    )}
                  </td>
                  <td>
                    <button
                      className="btn btn-primary btn-sm"
                      disabled={!isDirty || updateMut.isPending}
                      onClick={() => handleSave(t.threshold_key, t.threshold_value)}
                    >
                      {updateMut.isPending && updateMut.variables?.key === t.threshold_key
                        ? 'Enregistrement...'
                        : 'Enregistrer'}
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
