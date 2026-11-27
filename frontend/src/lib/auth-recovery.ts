// Remember recovery intent across reloads, without storing credentials here.
const recoveryKey = 'project-hub-recovery-user';
let recoveryUser: string | null = null;
try { recoveryUser = sessionStorage.getItem(recoveryKey); } catch { /* Storage may be disabled. */ }

export const authLinkError = typeof window !== 'undefined' &&
    [new URLSearchParams(window.location.search), new URLSearchParams(window.location.hash.slice(1))]
        .some(params => params.has('error') || params.has('error_code'));

export function isRecovery(userId?: string) { return !!userId && recoveryUser === userId; }
export function recordRecovery(userId: string | null) {
    recoveryUser = userId;
    try {
        if (userId) sessionStorage.setItem(recoveryKey, userId); else sessionStorage.removeItem(recoveryKey);
    } catch { /* In-memory recovery still works without storage. */ }
}
