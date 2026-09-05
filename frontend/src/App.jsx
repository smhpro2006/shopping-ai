import { createContext, useContext, useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import SearchPage from './pages/SearchPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import AccountPage from './pages/AccountPage'
import ProductPage from './pages/ProductPage'
import ComparePage from './pages/ComparePage'
import { api } from './api'

export const AuthContext = createContext(null)
export const useAuth = () => useContext(AuthContext)

export const CompareContext = createContext(null)
export const useCompare = () => useContext(CompareContext)

function PrivateRoute({ children }) {
  const { user } = useAuth()
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [compareIds, setCompareIds] = useState([])

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { setLoading(false); return }
    api.me()
      .then(data => { if (data?.id) setUser(data) })
      .finally(() => setLoading(false))
  }, [])

  const login = (token, userData) => {
    localStorage.setItem('token', token)
    setUser(userData)
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  const toggleCompare = (id) =>
    setCompareIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : prev.length < 3 ? [...prev, id] : prev
    )

  const clearCompare = () => setCompareIds([])

  if (loading) return <div className="loading"><div className="spinner" /></div>

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      <CompareContext.Provider value={{ compareIds, toggleCompare, clearCompare }}>
        <BrowserRouter>
          <Navbar />
          <Routes>
            <Route path="/" element={<SearchPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/product/:id" element={<ProductPage />} />
            <Route path="/compare" element={<ComparePage />} />
            <Route path="/dashboard" element={<PrivateRoute><DashboardPage /></PrivateRoute>} />
            <Route path="/account" element={<PrivateRoute><AccountPage /></PrivateRoute>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </CompareContext.Provider>
    </AuthContext.Provider>
  )
}
