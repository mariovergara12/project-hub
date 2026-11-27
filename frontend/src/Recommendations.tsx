import { useState } from 'react';
import { Link } from 'react-router-dom';
import { EmptyState, Icon, PageLoading, ProjectCard } from './ui';
import { useResource } from './use-resource';
import type { RecommendedProjects, RecommendationProfileField } from './types';

const fieldLabels: Record<RecommendationProfileField, string> = {
    skills: 'skills', interests: 'interests', availability_hours: 'weekly availability', experience_years: 'experience',
};

export function ProjectRecommendations() {
    const resource = useResource<RecommendedProjects>('/projects/recommended');
    const [expanded, setExpanded] = useState(false);
    const data = resource.data;
    const needsProfile = data?.missing_fields.length === 4;
    const visible = data?.items.slice(0, expanded ? 10 : 3) || [];
    return <section className="recommendations" aria-labelledby="recommendations-heading" aria-busy={resource.loading}>
        <div className="recommendation-heading"><div><p className="eyebrow">A good place to start</p><h2 id="recommendations-heading">Recommended for you</h2><p>Open projects that fit what you’ve shared in your profile.</p></div><div className="recommendation-actions"><Link to="/profile">Update profile <Icon name="arrow" /></Link><button aria-label="Refresh recommendations" disabled={resource.loading} onClick={resource.reload}>Refresh</button></div></div>
        {resource.loading && <PageLoading>Finding projects for you…</PageLoading>}
        {resource.error && <p role="alert">We couldn’t load your recommendations. You can browse all projects below. <button onClick={resource.reload}>Retry recommendations</button></p>}
        {data && <>
            {needsProfile ? <EmptyState title="Make your first matches" description="Add skills, interests, weekly availability, or experience to your profile. We’ll use those details to find projects for you."><Link className="button" to="/profile">Set up your profile</Link></EmptyState> : <>
                {data.missing_fields.length > 0 && <p className="recommendation-profile-note"><Icon name="user" /><span>For better matches, add {data.missing_fields.map(field => fieldLabels[field]).join(', ')} to your <Link to="/profile">profile</Link>.</span></p>}
                {data.items.length === 0 ? <EmptyState title="No matches right now" description="Try adding more profile details, or explore all projects below. New matches appear as projects open up." /> : <>
                    <div className="project-cards recommendation-cards">{visible.map(item => <ProjectCard key={item.project.id} project={item.project} details={<div className="recommendation-fit">
                        <p className="match-score" aria-label={`${item.score} match points out of 100`}><Icon name="check" /><strong>{item.score}</strong><span>/ 100 match points</span></p>
                        <ul className="match-reasons" aria-label={`Why ${item.project.title} matches`}>{item.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul>
                        {item.cautions.length > 0 && <details className="match-cautions"><summary>{item.cautions.length} {item.cautions.length === 1 ? 'requirement' : 'requirements'} to check</summary><ul>{item.cautions.map(note => <li key={note}>{note}</li>)}</ul></details>}
                    </div>} />)}</div>
                    {data.items.length > 3 && <div className="recommendation-more"><button aria-expanded={expanded} onClick={() => setExpanded(value => !value)}>{expanded ? 'Show fewer matches' : `Show all ${data.items.length} matches`}</button></div>}
                    <details className="recommendation-help"><summary>How matching works</summary><p>Shared skills contribute up to 50 points, with required skills counting twice as much as optional skills. Shared interests add up to 25 points. Meeting the time commitment adds 15, and meeting the experience requirement adds 10. Missing details earn no points. Scores change when your profile or a project’s requirements change.</p></details>
                </>}
            </>}
        </>}
    </section>;
}
