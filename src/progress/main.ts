import './progress.css';

type IssueStatus = 'complete' | 'review' | 'not-started';
type StageStatus = 'complete' | 'open' | 'review' | 'not-started';

interface Issue {
  id: string;
  milestone: string;
  title: string;
  status: IssueStatus;
  summary: string;
}

interface Milestone {
  id: string;
  title: string;
  status: StageStatus;
  detail: string;
}

interface ForecastItem {
  id: string;
  title: string;
  minDays: number;
  maxDays: number;
  group: 'mvp' | 'polish';
}

interface CurrentWork {
  label: string;
  state: 'done' | 'underway' | 'next';
}

interface Risk {
  level: 'open' | 'watch';
  title: string;
  detail: string;
}

interface Evidence {
  label: string;
  path: string;
}

interface ProjectProgress {
  schemaVersion: number;
  asOf: string;
  project: string;
  currentIssue: string;
  currentNote: string;
  nextAction: string;
  currentWork: CurrentWork[];
  mvpMilestone: string;
  polishMilestone: string;
  issues: Issue[];
  milestones: Milestone[];
  forecast: ForecastItem[];
  risks: Risk[];
  forecastNotes: string[];
  evidence: Evidence[];
}

function requiredElement<T extends Element>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) throw new Error(`Project dashboard is missing ${selector}.`);
  return element;
}

const dashboard = requiredElement<HTMLElement>('#dashboard');
const refreshButton = requiredElement<HTMLButtonElement>('#refresh');
const liveMessage = requiredElement<HTMLElement>('#live-message');
const reportDate = requiredElement<HTMLElement>('#report-date');
const refreshedAt = requiredElement<HTMLElement>('#refreshed-at');

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => {
    const entities: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;',
    };
    return entities[character] ?? character;
  });
}

function isProgress(value: unknown): value is ProjectProgress {
  if (!value || typeof value !== 'object') return false;
  const data = value as Partial<ProjectProgress>;
  const validStatuses = ['complete', 'review', 'not-started'];
  return (
    data.schemaVersion === 1 &&
    typeof data.asOf === 'string' &&
    typeof data.currentIssue === 'string' &&
    typeof data.currentNote === 'string' &&
    typeof data.nextAction === 'string' &&
    Array.isArray(data.currentWork) &&
    data.currentWork.every(
      (work) =>
        typeof work.label === 'string' &&
        ['done', 'underway', 'next'].includes(work.state),
    ) &&
    typeof data.mvpMilestone === 'string' &&
    typeof data.polishMilestone === 'string' &&
    Array.isArray(data.issues) &&
    data.issues.every(
      (issue) =>
        typeof issue.id === 'string' &&
        typeof issue.milestone === 'string' &&
        typeof issue.title === 'string' &&
        validStatuses.includes(issue.status) &&
        typeof issue.summary === 'string',
    ) &&
    Array.isArray(data.milestones) &&
    Array.isArray(data.forecast) &&
    data.forecast.every(
      (item) =>
        typeof item.id === 'string' &&
        typeof item.title === 'string' &&
        typeof item.minDays === 'number' &&
        typeof item.maxDays === 'number' &&
        ['mvp', 'polish'].includes(item.group),
    ) &&
    Array.isArray(data.risks) &&
    Array.isArray(data.forecastNotes) &&
    Array.isArray(data.evidence)
  );
}

function statusLabel(status: IssueStatus | StageStatus): string {
  const labels: Record<IssueStatus | StageStatus, string> = {
    complete: 'Complete',
    open: 'Gate open',
    review: 'Review pending',
    'not-started': 'Not started · authorization pending',
  };
  return labels[status];
}

function statusClass(status: IssueStatus | StageStatus): string {
  return `status-${status}`;
}

function formatDate(date: string): string {
  const parsed = new Date(`${date}T12:00:00`);
  if (Number.isNaN(parsed.valueOf())) return date;
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(
    parsed,
  );
}

function renderMilestones(milestones: Milestone[]): string {
  return milestones
    .map(
      (milestone) => `
        <article class="milestone-card ${statusClass(milestone.status)}">
          <div class="milestone-topline"><span>${escapeHtml(milestone.id)}</span><span class="status-dot" aria-hidden="true"></span></div>
          <h3>${escapeHtml(milestone.title)}</h3>
          <p>${escapeHtml(milestone.detail)}</p>
          <span class="status-pill ${statusClass(milestone.status)}">${statusLabel(milestone.status)}</span>
        </article>`,
    )
    .join('');
}

function renderIssues(issues: Issue[]): string {
  return issues
    .map(
      (issue) => `
        <tr>
          <td class="issue-id">${escapeHtml(issue.id)}</td>
          <td><span class="milestone-tag">${escapeHtml(issue.milestone)}</span></td>
          <td><strong>${escapeHtml(issue.title)}</strong><span class="issue-summary">${escapeHtml(issue.summary)}</span></td>
          <td><span class="status-pill ${statusClass(issue.status)}">${statusLabel(issue.status)}</span></td>
        </tr>`,
    )
    .join('');
}

function renderForecast(items: ForecastItem[]): string {
  const mvp = items.filter((item) => item.group === 'mvp');
  const polish = items.filter((item) => item.group === 'polish');
  const rows = (list: ForecastItem[]) =>
    list
      .map(
        (item) => `
          <div class="forecast-row">
            <div class="forecast-task"><span class="issue-id">${escapeHtml(item.id)}</span><strong>${escapeHtml(item.title)}</strong></div>
            <span class="estimate">${item.minDays}–${item.maxDays}<small>days</small></span>
          </div>`,
      )
      .join('');
  return `<div class="forecast-list">${rows(mvp)}</div><div class="forecast-divider"></div><div class="forecast-list forecast-polish">${rows(polish)}</div>`;
}

function estimateRange(items: ForecastItem[]): { min: number; max: number } {
  return items.reduce(
    (range, item) => ({
      min: range.min + item.minDays,
      max: range.max + item.maxDays,
    }),
    { min: 0, max: 0 },
  );
}

function renderRisks(risks: Risk[]): string {
  return risks
    .map(
      (risk) => `
        <article class="risk-item risk-${escapeHtml(risk.level)}">
          <span class="risk-marker" aria-hidden="true"></span>
          <div><h3>${escapeHtml(risk.title)}</h3><p>${escapeHtml(risk.detail)}</p></div>
        </article>`,
    )
    .join('');
}

function renderEvidence(evidence: Evidence[]): string {
  return evidence
    .map(
      (item) => `
        <div class="evidence-row">
          <span>${escapeHtml(item.label)}</span>
          <code>${escapeHtml(item.path)}</code>
        </div>`,
    )
    .join('');
}

function render(data: ProjectProgress): void {
  const completed = data.issues.filter(
    (issue) => issue.status === 'complete',
  ).length;
  const review = data.issues.filter(
    (issue) => issue.status === 'review',
  ).length;
  const total = data.issues.length;
  const percent = total === 0 ? 0 : Math.round((completed / total) * 100);
  const current = data.issues.find((issue) => issue.id === data.currentIssue);
  const mvpForecast = data.forecast.filter((item) => item.group === 'mvp');
  const polishForecast = data.forecast.filter(
    (item) => item.group === 'polish',
  );
  const mvpEstimate = estimateRange(mvpForecast);
  const totalEstimate = estimateRange([...mvpForecast, ...polishForecast]);
  const currentStatus = current?.status ?? 'not-started';
  const workStateClass: Record<CurrentWork['state'], string> = {
    done: 'done',
    underway: 'underway',
    next: 'pending',
  };

  reportDate.textContent = formatDate(data.asOf);
  dashboard.innerHTML = `
    <section class="summary-grid" aria-label="Project summary">
      <article class="summary-card progress-summary">
        <div class="summary-label">ISSUES COMPLETED <span class="summary-icon" aria-hidden="true">↗</span></div>
        <div class="summary-value">${completed}<span> / ${total}</span></div>
        <div class="progress-track" role="progressbar" aria-label="Completed project issues" aria-valuemin="0" aria-valuemax="${total}" aria-valuenow="${completed}"><span style="width:${percent}%"></span></div>
        <div class="summary-foot"><span>${percent}% of planned issue list</span><span>${total - completed - review} still ahead</span></div>
      </article>
      <article class="summary-card current-summary">
        <div class="summary-label">CURRENT ISSUE <span class="status-pill ${statusClass(currentStatus)}">${statusLabel(currentStatus)}</span></div>
        <div class="summary-value issue-value">${escapeHtml(data.currentIssue)}</div>
        <p>${escapeHtml(current?.title ?? 'Current issue details unavailable')}</p>
        <div class="summary-foot"><span>${escapeHtml(data.currentNote)}</span><span>${escapeHtml(data.nextAction)}</span></div>
      </article>
      <article class="summary-card mvp-summary">
        <div class="summary-label">PLAYABLE MVP TARGET <span class="target-icon" aria-hidden="true">◎</span></div>
        <div class="summary-value">${escapeHtml(data.mvpMilestone)}</div>
        <p>Walk and fly across real terrain with buildings and roads.</p>
        <div class="summary-foot"><span>${mvpEstimate.min}–${mvpEstimate.max} focused workdays</span><span>planning range</span></div>
      </article>
    </section>

    <section class="focus-grid">
      <article class="panel current-panel">
        <div class="section-kicker">NOW · ${escapeHtml(data.currentIssue)}</div>
        <div class="current-heading"><div><h2>${escapeHtml(current?.title ?? 'Current issue')}</h2><p>${escapeHtml(current?.summary ?? '')}</p></div><span class="large-status-mark">${escapeHtml(data.currentIssue.slice(-3))}</span></div>
        <div class="current-work">
          ${data.currentWork
            .map(
              (work, index) =>
                `<div><span class="step-index">${String(index + 1).padStart(2, '0')}</span><span>${escapeHtml(work.label)}</span><span class="step-state ${workStateClass[work.state]}">${escapeHtml(work.state.toUpperCase())}</span></div>`,
            )
            .join('')}
        </div>
        <div class="button-row">
          <a class="primary-link" href="/?world=torquay-poc-001">Open EA terrain <span aria-hidden="true">↗</span></a>
          <a class="secondary-link" href="/">Open synthetic viewer</a>
        </div>
      </article>

      <aside class="panel gate-panel">
        <div class="section-kicker">OPEN GATE · M2</div>
        <div class="gate-status"><span class="gate-symbol" aria-hidden="true">!</span><h2>AOI coverage still pending</h2></div>
        <p>The EA terrain check passes. OSM/OS building and road counts are not checked, so the area is not approved or frozen.</p>
        <div class="gate-foot"><span>selection_status</span><code>selected_pending_coverage</code></div>
        <div class="gate-foot"><span>coverage_status</span><code>not_checked</code></div>
      </aside>
    </section>

    <section class="panel roadmap-panel">
      <div class="section-heading">
        <div><div class="section-kicker">MILESTONES</div><h2>From synthetic world to walkable Torquay</h2></div>
        <div class="legend"><span><i class="legend-complete"></i>Complete</span><span><i class="legend-active"></i>Active / open</span><span><i class="legend-queued"></i>Planned</span></div>
      </div>
      <div class="milestone-grid">${renderMilestones(data.milestones)}</div>
    </section>

    <section class="lower-grid">
      <article class="panel issue-panel">
        <div class="section-heading compact-heading"><div><div class="section-kicker">ISSUE TRACKER</div><h2>All ${total} planned issues</h2></div><span class="small-note">${review} in review · future work needs authorization</span></div>
        <div class="table-wrap"><table><thead><tr><th>Issue</th><th>Milestone</th><th>Work item</th><th>Status</th></tr></thead><tbody>${renderIssues(data.issues)}</tbody></table></div>
      </article>

      <div class="right-column">
        <article class="panel forecast-panel">
          <div class="section-heading compact-heading"><div><div class="section-kicker">LOOKING AHEAD</div><h2>MVP runway</h2></div><span class="target-badge">${escapeHtml(data.mvpMilestone)} · PLAYABLE</span></div>
          ${renderForecast(data.forecast)}
          <div class="forecast-total"><span>To playable ${escapeHtml(data.mvpMilestone)}</span><strong>${mvpEstimate.min}–${mvpEstimate.max} <small>focused workdays</small></strong></div>
          <div class="forecast-total polish-total"><span>Including ${escapeHtml(data.polishMilestone)} handback</span><strong>${totalEstimate.min}–${totalEstimate.max} <small>focused workdays total</small></strong></div>
          <ul class="forecast-notes">${data.forecastNotes.map((note) => `<li>${escapeHtml(note)}</li>`).join('')}</ul>
        </article>

        <article class="panel risk-panel">
          <div class="section-heading compact-heading"><div><div class="section-kicker">WATCHLIST</div><h2>Things that can move the estimate</h2></div></div>
          <div class="risk-list">${renderRisks(data.risks)}</div>
        </article>
      </div>
    </section>

    <section class="panel evidence-panel">
      <div class="section-heading compact-heading"><div><div class="section-kicker">SOURCE NOTES</div><h2>What this snapshot is based on</h2></div><span class="small-note">As of ${escapeHtml(formatDate(data.asOf))}</span></div>
      <div class="evidence-list">${renderEvidence(data.evidence)}</div>
    </section>`;
  dashboard.setAttribute('aria-busy', 'false');
}

async function refreshProgress(): Promise<void> {
  refreshButton.disabled = true;
  liveMessage.textContent = 'Refreshing the local project snapshot…';
  try {
    const response = await fetch(
      `/project-progress.json?refresh=${Date.now()}`,
      { cache: 'no-store' },
    );
    if (!response.ok)
      throw new Error(`Snapshot request returned ${response.status}.`);
    const payload: unknown = await response.json();
    if (!isProgress(payload))
      throw new Error('Snapshot format is not recognized.');
    render(payload);
    refreshedAt.textContent = new Intl.DateTimeFormat(undefined, {
      hour: 'numeric',
      minute: '2-digit',
    }).format(new Date());
    liveMessage.textContent = `Updated from the local project snapshot. Report date: ${formatDate(payload.asOf)}.`;
  } catch (error) {
    dashboard.setAttribute('aria-busy', 'false');
    liveMessage.textContent = `Could not refresh project status: ${error instanceof Error ? error.message : 'unknown error'}`;
  } finally {
    refreshButton.disabled = false;
  }
}

refreshButton.addEventListener('click', () => void refreshProgress());
void refreshProgress();
