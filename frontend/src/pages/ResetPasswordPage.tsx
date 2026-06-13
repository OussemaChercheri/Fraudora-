import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { z } from 'zod'

import { resetPassword } from '../api/auth'

const resetSchema = z
  .object({
    new_password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm_password: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  })

type ResetFormValues = z.infer<typeof resetSchema>

export default function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetFormValues>({
    resolver: zodResolver(resetSchema),
  })

  const mutation = useMutation({
    mutationFn: (newPassword: string) => resetPassword(token, newPassword),
    onSuccess: () => navigate('/login'),
  })

  const onSubmit = (values: ResetFormValues) => {
    mutation.mutate(values.new_password)
  }

  if (!token) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h1>Invalid reset link</h1>
          <p className="auth-subtitle">No reset token found in the URL.</p>
          <Link to="/forgot-password" className="link">
            Request a new reset link
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Reset password</h1>
        <p className="auth-subtitle">Choose a new password for your account.</p>

        <form className="auth-form" onSubmit={handleSubmit(onSubmit)}>
          <div className="form-field">
            <label htmlFor="new_password">New password</label>
            <input
              id="new_password"
              type="password"
              autoComplete="new-password"
              {...register('new_password')}
            />
            {errors.new_password && (
              <span className="field-error">{errors.new_password.message}</span>
            )}
          </div>

          <div className="form-field">
            <label htmlFor="confirm_password">Confirm password</label>
            <input
              id="confirm_password"
              type="password"
              autoComplete="new-password"
              {...register('confirm_password')}
            />
            {errors.confirm_password && (
              <span className="field-error">
                {errors.confirm_password.message}
              </span>
            )}
          </div>

          {mutation.isError && (
            <div className="form-error">
              Invalid or expired reset token. Please request a new one.
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={mutation.isPending}
          >
            {mutation.isPending ? 'Resetting...' : 'Reset password'}
          </button>
        </form>

        <Link to="/login" className="link">
          Back to login
        </Link>
      </div>
    </div>
  )
}
