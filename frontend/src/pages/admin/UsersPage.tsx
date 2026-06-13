import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { createUser, deactivateUser, fetchUsers } from '../../api/users'
import type { UserRole, UserResponse } from '../../types/user'

const ROLES: UserRole[] = ['ADMIN', 'FINANCE', 'COMPTABLE', 'VIEWER']

const createUserSchema = z.object({
  full_name: z.string().min(1, 'Full name is required'),
  email: z.email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  role: z.enum(['ADMIN', 'FINANCE', 'COMPTABLE', 'VIEWER']),
})

type CreateUserFormValues = z.infer<typeof createUserSchema>

function RoleBadge({ role }: { role: UserRole }) {
  return <span className={`role-badge role-badge--${role.toLowerCase()}`}>{role}</span>
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export default function UsersPage() {
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)

  const { data: users = [], isLoading, isError } = useQuery({
    queryKey: ['users'],
    queryFn: fetchUsers,
  })

  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setModalOpen(false)
      reset()
    },
  })

  const deactivateMutation = useMutation({
    mutationFn: deactivateUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateUserFormValues>({
    resolver: zodResolver(createUserSchema),
    defaultValues: { role: 'COMPTABLE' },
  })

  const onCreateSubmit = (values: CreateUserFormValues) => {
    createMutation.mutate(values)
  }

  const handleDeactivate = (user: UserResponse) => {
    const confirmed = window.confirm(
      `Deactivate ${user.full_name}? They will no longer be able to sign in.`,
    )
    if (confirmed) {
      deactivateMutation.mutate(user.id)
    }
  }

  return (
    <div className="page-container page-container--wide">
      <div className="page-header">
        <h1>User management</h1>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setModalOpen(true)}
        >
          Create user
        </button>
      </div>

      {isLoading && <p>Loading users...</p>}
      {isError && <p className="form-error">Failed to load users.</p>}

      {!isLoading && !isError && (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Full name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.full_name}</td>
                  <td>{user.email}</td>
                  <td>
                    <RoleBadge role={user.role} />
                  </td>
                  <td>
                    <span
                      className={`status-badge ${user.is_active ? 'status-badge--active' : 'status-badge--inactive'}`}
                    >
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>{formatDate(user.created_at)}</td>
                  <td>
                    {user.is_active && (
                      <button
                        type="button"
                        className="btn btn-danger btn-sm"
                        disabled={deactivateMutation.isPending}
                        onClick={() => handleDeactivate(user)}
                      >
                        Deactivate
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modalOpen && (
        <div className="modal-overlay" onClick={() => setModalOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Create user</h2>
            <form className="auth-form" onSubmit={handleSubmit(onCreateSubmit)}>
              <div className="form-field">
                <label htmlFor="full_name">Full name</label>
                <input id="full_name" type="text" {...register('full_name')} />
                {errors.full_name && (
                  <span className="field-error">{errors.full_name.message}</span>
                )}
              </div>

              <div className="form-field">
                <label htmlFor="email">Email</label>
                <input id="email" type="email" {...register('email')} />
                {errors.email && (
                  <span className="field-error">{errors.email.message}</span>
                )}
              </div>

              <div className="form-field">
                <label htmlFor="password">Password</label>
                <input id="password" type="password" {...register('password')} />
                {errors.password && (
                  <span className="field-error">{errors.password.message}</span>
                )}
              </div>

              <div className="form-field">
                <label htmlFor="role">Role</label>
                <select id="role" {...register('role')}>
                  {ROLES.map((role) => (
                    <option key={role} value={role}>
                      {role}
                    </option>
                  ))}
                </select>
                {errors.role && (
                  <span className="field-error">{errors.role.message}</span>
                )}
              </div>

              {createMutation.isError && (
                <div className="form-error">Failed to create user.</div>
              )}

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSubmitting || createMutation.isPending}
                >
                  {createMutation.isPending ? 'Creating...' : 'Create user'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
