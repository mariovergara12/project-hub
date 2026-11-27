import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './auth-context';

export function RequireAuth() {
    const { session, loading, recovery } = useAuth();
    if (loading) return <p role="status">Loading your session…</p>;
    if (recovery) return <Navigate to="/reset-password" replace />;
    return session ? <Outlet key={session.user.id} /> : <Navigate to="/" replace />;
}
