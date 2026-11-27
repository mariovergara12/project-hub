import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from './api';
import { PageHeading, PageLoading } from './ui';
import { useResource } from './use-resource';
import type { Me, ProfileData } from './types';
import { ProfileSelections } from './ProfileSelections';

function ProfileForm({ me, saved }: { me: Me; saved: () => void }) {
    const [pending, setPending] = useState(false);
    const submitting = useRef(false);
    const [error, setError] = useState('');
    const profile = me.profile;
    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (submitting.current) return;
        const values = new FormData(event.currentTarget);
        const text = (name: string) => String(values.get(name) || '').trim() || null;
        const integer = (name: string) => {
            const value = text(name);
            return value === null ? null : Number(value);
        };
        submitting.current = true;
        setPending(true);
        setError('');
        try {
            await api.patch<ProfileData>('/me/profile', {
                display_name: text('display_name'), university: text('university'),
                major: text('major'), department: text('department'), bio: text('bio'),
                learning_goals: text('learning_goals'), availability_hours: integer('availability_hours'),
                experience_years: integer('experience_years'),
            });
            saved();
        } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not save your profile.'); }
        finally { submitting.current = false; setPending(false); }
    }
    return <form onSubmit={submit} aria-busy={pending}>
        <fieldset disabled={pending} className="profile-fields">
            <legend>{profile ? 'Edit your profile' : 'Complete your profile'}</legend>
            <label>Display name<input name="display_name" required maxLength={150} defaultValue={profile?.display_name || ''} /></label>
            <label>University<input name="university" maxLength={200} defaultValue={profile?.university || ''} /></label>
            <label>Major<input name="major" maxLength={150} defaultValue={profile?.major || ''} /></label>
            <label>Department<input name="department" maxLength={150} defaultValue={profile?.department || ''} /></label>
            <label className="field-wide">Bio<textarea name="bio" maxLength={5000} defaultValue={profile?.bio || ''} /></label>
            <label>Weekly availability (hours)<input name="availability_hours" type="number" min={0} max={168} step={1} defaultValue={profile?.availability_hours ?? ''} /></label>
            <label>Experience (years)<input name="experience_years" type="number" min={0} max={100} step={1} defaultValue={profile?.experience_years ?? ''} /></label>
            <label className="field-wide">Learning goals<textarea name="learning_goals" maxLength={2000} defaultValue={profile?.learning_goals || ''} /></label>
            <button type="submit">{pending ? 'Saving…' : 'Save profile'}</button>
        </fieldset>
        {error && <p role="alert">{error}</p>}
    </form>;
}

export function Profile() {
    const [params] = useSearchParams();
    const [selectionCounts, setSelectionCounts] = useState<Partial<Record<'skills' | 'interests', number>>>({});
    const resource = useResource<Me>('/me');
    const [message, setMessage] = useState('');
    return <main className="app-page">
        <PageHeading eyebrow="Your account" title="Your profile" description="Share what you know, what interests you, and what you'd like to learn next." />
        {message && <p role="status">{message}</p>}
        {resource.loading && <PageLoading>Loading your profile…</PageLoading>}
        {resource.error && <div role="alert">{resource.error.message} <button onClick={resource.reload}>Retry profile</button></div>}
        {resource.data && (params.has('welcome') || !resource.data.profile) && <section className="onboarding-panel" aria-label="Profile setup"><h2>Welcome to Project Hub</h2><p>Start with your name so teammates know who you are. Skills and interests are optional and help people find a good fit.</p><ol className="onboarding-steps"><li>{resource.data.profile ? '✓ Name saved' : 'Add your display name'}</li><li>{(selectionCounts.skills ?? resource.data.skills.length) ? '✓ Skills saved' : 'Choose skills (optional)'}</li><li>{(selectionCounts.interests ?? resource.data.interests.length) ? '✓ Interests saved' : 'Choose interests (optional)'}</li></ol><nav className="subnav">{resource.data.profile && <Link className="button button-primary" to="/main">Continue to projects</Link>}<Link to="/main">Explore projects now</Link></nav></section>}
        {resource.data && <section className="profile-panel">
            <div className="account-facts"><p>Role: <strong>{resource.data.role}</strong></p><p>Faculty verification: <strong>{resource.data.faculty_verified_at ? 'Verified' : 'Not verified'}</strong></p></div>
            <ProfileForm me={resource.data} saved={() => { setMessage('Profile saved.'); resource.reload(); }} />
            <ProfileSelections me={resource.data} onSaved={(kind, items) => setSelectionCounts(counts => ({ ...counts, [kind]: items.length }))} />
        </section>}
    </main>;
}

export default Profile;
