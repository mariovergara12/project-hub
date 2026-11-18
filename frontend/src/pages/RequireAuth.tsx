import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../auth-context';

export function RequireAuth() {
    const { session, loading } = useAuth();
    if (loading) return <p role="status">Loading your session…</p>;
    return session ? <Outlet key={session.user.id} /> : <Navigate to="/" replace />;
}
