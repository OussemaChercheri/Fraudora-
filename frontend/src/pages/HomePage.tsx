import { useQuery } from '@tanstack/react-query'

import { fetchHealth } from '../api/health'
import { APP_NAME } from '../utils/constants'

export default function HomePage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
  })

  return (
    <section>
      <h2>Welcome to {APP_NAME}</h2>
      <p>Fraud detection platform powered by AI.</p>
      {isLoading && <p>Checking API status...</p>}
      {isError && <p>Unable to reach the backend API.</p>}
      {data && <p>API status: {data.status}</p>}
    </section>
  )
}
