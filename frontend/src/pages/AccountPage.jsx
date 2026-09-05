import { useAuth } from '../App'
import { useNavigate } from 'react-router-dom'

export default function AccountPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  if (!user) return null

  return (
    <div className="page">
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '1.5rem' }}>Account</h1>
      <div className="section-card">
        <div className="section-card-header">Profile</div>
        <div style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Email address</label>
            <div style={{
              padding: '0.55rem 0.8rem',
              background: 'var(--bg)',
              borderRadius: 6,
              border: '1px solid var(--border)',
              fontSize: '0.9rem',
            }}>
              {user.email}
            </div>
          </div>
          <div>
            <button className="btn btn-danger" onClick={handleLogout}>Log out</button>
          </div>
        </div>
      </div>
    </div>
  )
}
