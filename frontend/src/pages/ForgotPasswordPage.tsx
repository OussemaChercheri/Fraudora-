import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { z } from 'zod'

import { forgotPassword } from '../api/auth'

const forgotSchema = z.object({
  email: z.email('Invalid email address'),
})

type ForgotFormValues = z.infer<typeof forgotSchema>

export default function ForgotPasswordPage() {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotFormValues>({
    resolver: zodResolver(forgotSchema),
  })

  const mutation = useMutation({
    mutationFn: (email: string) => forgotPassword(email),
  })

  const onSubmit = (values: ForgotFormValues) => {
    mutation.mutate(values.email)
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Forgot password</h1>
        <p className="auth-subtitle">
          Enter your email and we will send you a reset link.
        </p>

        {mutation.isSuccess ? (
          <div className="form-success">Check your email</div>
        ) : (
          <form className="auth-form" onSubmit={handleSubmit(onSubmit)}>
            <div className="form-field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                {...register('email')}
              />
              {errors.email && (
                <span className="field-error">{errors.email.message}</span>
              )}
            </div>

            {mutation.isError && (
              <div className="form-error">
                Something went wrong. Please try again.
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary"
              disabled={mutation.isPending}
            >
              {mutation.isPending ? 'Sending...' : 'Send reset link'}
            </button>
          </form>
        )}

        <Link to="/login" className="link">
          Back to login
        </Link>
      </div>
    </div>
  )
}
