import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../App'
import { useCompare } from '../App'

export default function Navbar() {
  const { user, logout } = useAuth()
  const { compareIds } = useCompare()
  const location = useLocation()
  const navigate = useNavigate()

  const isActive = (path) => location.pathname === path ? 'nav-link active' : 'nav-link'

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">Shopping AI</Link>
      <div className="navbar-links">
        <Link to="/" className={isActive('/')}>Search</Link>
        {compareIds.length > 0 && (
          <Link to="/compare" className={isActive('/compare')} style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            Compare
            <span style={{
              background: 'var(--primary)',
              color: '#fff',
              fontSize: '0.68rem',
              fontWeight: 700,
              borderRadius: '10px',
              padding: '0.1rem 0.45rem',
            }}>{compareIds.length}</span>
          </Link>
        )}
        {user ? (
          <>
            <Link to="/account" className={isActive('/account')}>Account</Link>
            <Link to="/dashboard" className={isActive('/dashboard')}>Dashboard</Link>
            <button className="btn btn-ghost" onClick={handleLogout}>Logout</button>
          </>
        ) : (
          <>
            <Link to="/login" className={isActive('/login')}>Login</Link>
            <Link to="/register">
              <button className="btn btn-primary">Sign up</button>
            </Link>
          </>
        )}
      </div>
    </nav>
  )
}
