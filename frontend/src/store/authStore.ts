import { create } from 'zustand'

import { loginUser, logoutUser } from '../api/auth'
import type { UserResponse } from '../types/user'
import {
  ACCESS_TOKEN_KEY,
  getStoredToken,
  parseUserFromToken,
} from '../utils/auth'

interface AuthState {
  user: UserResponse | null
  accessToken: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  setUser: (user: UserResponse | null) => void
}

const storedToken = getStoredToken()

export const useAuthStore = create<AuthState>((set) => ({
  user: storedToken ? parseUserFromToken(storedToken) : null,
  accessToken: storedToken,
  isAuthenticated: !!storedToken,

  login: async (email, password) => {
    const tokens = await loginUser(email, password)
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token)
    const user = parseUserFromToken(tokens.access_token)
    set({
      accessToken: tokens.access_token,
      isAuthenticated: true,
      user,
    })
  },

  logout: async () => {
    try {
      await logoutUser()
    } catch {
      // Token may already be invalid; still clear local state.
    }
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    set({
      accessToken: null,
      isAuthenticated: false,
      user: null,
    })
  },

  setUser: (user) => set({ user }),
}))
