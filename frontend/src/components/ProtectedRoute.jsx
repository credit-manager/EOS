import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'

function ProtectedRoute({ children }) {
  const location = useLocation()
  const isAuthenticated = localStorage.getItem('eos_token')

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return children
}

export default ProtectedRoute
