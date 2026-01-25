import { useEffect, useState } from 'react';
import { adminDashboardApi } from '../../services/api';
import type { DashboardStats, AILog } from '../../services/api';
import { SPORT_LABELS } from '../../constants/labels';

const FEATURE_LABELS: Record<string, string> = {
  content: '콘텐츠 생성',
  feedback: '피드백 생성',
  recommendation: '강습 추천',
  chat: '채팅',
};

const FEATURE_ICONS: Record<string, string> = {
  content: 'edit_note',
  feedback: 'feedback',
  recommendation: 'recommend',
  chat: 'forum',
};

const SPORT_COLORS: Record<string, string> = {
  swimming: 'bg-cyan-500',
  golf: 'bg-orange-500',
  tennis: 'bg-lime-500',
  yoga: 'bg-pink-500',
  pilates: 'bg-indigo-500',
  fitness: 'bg-red-500',
  other: 'bg-slate-500',
};

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [aiLogs, setAILogs] = useState<AILog[]>([]);
  const [loading, setLoading] = useState(true);
  const [aiLogsLoading, setAiLogsLoading] = useState(true);
  const [logFilter, setLogFilter] = useState<string>('');

  useEffect(() => {
    loadDashboard();
    loadAILogs();
  }, []);

  useEffect(() => {
    loadAILogs();
  }, [logFilter]);

  const loadDashboard = async () => {
    try {
      const res = await adminDashboardApi.getStats();
      setStats(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadAILogs = async () => {
    setAiLogsLoading(true);
    try {
      const res = await adminDashboardApi.getAILogs(logFilter || undefined, 0, 10);
      setAILogs(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setAiLogsLoading(false);
    }
  };

  if (loading || !stats) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-slate-500">데이터를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  // 종목별 최대값 계산 (progress bar 용)
  const maxSportCount = Math.max(...Object.values(stats.lessons.by_sport), 1);

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-slate-900 text-3xl font-black leading-tight tracking-tight">운영 대시보드</h1>
          <p className="text-slate-500 text-sm font-medium flex items-center gap-2">
            <span className="material-symbols-outlined text-base">calendar_today</span>
            {new Date(stats.period.start_date).toLocaleDateString('ko-KR')} ~ {new Date(stats.period.end_date).toLocaleDateString('ko-KR')}
          </p>
        </div>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-900 hover:bg-slate-50 transition-colors">
            <span className="material-symbols-outlined text-base">download</span>
            내보내기
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm font-bold shadow-md hover:bg-blue-600 transition-colors">
            <span className="material-symbols-outlined text-base">add</span>
            새 리포트
          </button>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
        {/* Lessons */}
        <MetricCard
          icon="library_books"
          title="강습"
          value={stats.lessons.total}
          color="blue"
          change={12}
          details={[
            { label: '발행됨', value: stats.lessons.published, highlight: true },
            { label: '초안', value: stats.lessons.draft },
          ]}
        />

        {/* Students */}
        <MetricCard
          icon="school"
          title="수강생"
          value={stats.enrollments.total}
          color="green"
          change={5.4}
          details={[
            { label: '신규', value: stats.enrollments.new_in_period, highlight: true },
            { label: '수료', value: stats.enrollments.completed_in_period },
          ]}
        />

        {/* Attendance */}
        <MetricCard
          icon="donut_large"
          title="평균 출석률"
          value={`${stats.enrollments.avg_attendance_rate}%`}
          color="yellow"
          change={0}
          details={[
            { label: '수강 중', value: stats.enrollments.in_progress, highlight: true },
            { label: '수료', value: stats.enrollments.completed },
          ]}
        />

        {/* AI Usage */}
        <MetricCard
          icon="smart_toy"
          title="AI 호출"
          value={stats.ai_usage.total_calls >= 1000 ? `${(stats.ai_usage.total_calls / 1000).toFixed(1)}k` : stats.ai_usage.total_calls}
          color="purple"
          change={22}
          details={[
            { label: '평균 응답', value: `${stats.ai_usage.avg_latency_ms}ms`, highlight: true },
            { label: '수정률', value: `${stats.ai_usage.edit_rate}%`, isWarning: stats.ai_usage.edit_rate > 10 },
          ]}
        />
      </div>

      {/* Middle Section: AI Features & Sport Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* AI Feature Usage */}
        <div className="lg:col-span-2 bg-white rounded-xl p-6 shadow-sm border border-slate-100">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <div>
              <h3 className="text-slate-900 text-xl font-bold leading-tight">AI 기능별 사용량</h3>
              <p className="text-slate-500 text-sm font-normal mt-1">플랫폼 전체 AI 도구 활용 현황</p>
            </div>
            {stats.ai_usage.total_tokens > 0 && (
              <div className="px-4 py-2 bg-primary/10 rounded-lg">
                <p className="text-primary text-sm font-bold">총 토큰: {stats.ai_usage.total_tokens.toLocaleString()}</p>
              </div>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(stats.ai_usage.by_feature).map(([feature, count]) => (
              <div
                key={feature}
                className="flex flex-col gap-3 rounded-lg border border-slate-200 p-4 hover:border-primary/50 transition-colors"
              >
                <div className="text-primary bg-primary/5 w-fit p-2 rounded-md">
                  <span className="material-symbols-outlined">{FEATURE_ICONS[feature] || 'smart_toy'}</span>
                </div>
                <div>
                  <h4 className="text-slate-900 text-base font-bold">{FEATURE_LABELS[feature] || feature}</h4>
                  <p className="text-slate-500 text-sm">{count.toLocaleString()} calls</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sport Distribution */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-100 flex flex-col h-full">
          <h3 className="text-slate-900 text-xl font-bold leading-tight mb-6">종목별 강습</h3>
          <div className="flex flex-col gap-4 flex-1 justify-center">
            {Object.entries(stats.lessons.by_sport).map(([sport, count]) => {
              const percentage = Math.round((count / maxSportCount) * 100);
              const colorClass = SPORT_COLORS[sport] || SPORT_COLORS.other;
              return (
                <div key={sport} className="flex items-center justify-between group">
                  <div className="flex items-center gap-3">
                    <span className={`size-3 rounded-full ${colorClass}`}></span>
                    <span className="text-slate-900 font-medium">{SPORT_LABELS[sport] || sport}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className={`h-full ${colorClass} rounded-full transition-all`} style={{ width: `${percentage}%` }}></div>
                    </div>
                    <span className="text-sm text-slate-500 font-medium w-8 text-right">{count}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* AI Logs Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="flex items-center gap-3">
            <h3 className="text-slate-900 text-xl font-bold leading-tight">최근 AI 로그</h3>
            {aiLogsLoading && (
              <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            )}
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <select
                value={logFilter}
                onChange={(e) => setLogFilter(e.target.value)}
                disabled={aiLogsLoading}
                className="appearance-none bg-background-light border border-slate-200 text-slate-900 text-sm rounded-lg pl-3 pr-10 py-2 focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
              >
                <option value="">전체</option>
                {Object.entries(FEATURE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-500">
                <span className="material-symbols-outlined text-sm">expand_more</span>
              </div>
            </div>
            <button className="text-sm text-primary font-medium hover:underline">전체 보기</button>
          </div>
        </div>

        {aiLogsLoading ? (
          <AILogsLoadingSkeleton />
        ) : aiLogs.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            <span className="material-symbols-outlined text-4xl text-slate-300 mb-2">search_off</span>
            <p>로그가 없습니다.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50">
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">시간</th>
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">기능</th>
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">토큰</th>
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">응답시간</th>
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">상태</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {aiLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                      {new Date(log.created_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary">
                        {FEATURE_LABELS[log.feature_type] || log.feature_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 font-mono">
                      {log.tokens_used?.toLocaleString() || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 font-mono">
                      {log.latency_ms ? `${Math.round(log.latency_ms)}ms` : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      {log.was_edited ? (
                        <span className="text-orange-500">수정됨</span>
                      ) : (
                        <span className="text-green-500">성공</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {aiLogs.length > 0 && (
          <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex justify-between items-center">
            <p className="text-sm text-slate-500">{aiLogs.length}개 항목 표시</p>
            <div className="flex gap-2">
              <button className="px-3 py-1 rounded border border-slate-200 bg-white text-sm text-slate-500 hover:bg-slate-50 disabled:opacity-50">
                이전
              </button>
              <button className="px-3 py-1 rounded border border-slate-200 bg-white text-sm text-slate-500 hover:bg-slate-50">
                다음
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Metric Card Component
function MetricCard({
  icon,
  title,
  value,
  color,
  change,
  details,
}: {
  icon: string;
  title: string;
  value: number | string;
  color: 'blue' | 'green' | 'yellow' | 'purple';
  change: number;
  details: { label: string; value: number | string; highlight?: boolean; isWarning?: boolean }[];
}) {
  const colorConfig = {
    blue: { border: 'border-l-blue-500', bg: 'bg-blue-50', text: 'text-blue-600', dot: 'bg-blue-500' },
    green: { border: 'border-l-green-500', bg: 'bg-green-50', text: 'text-green-600', dot: 'bg-green-500' },
    yellow: { border: 'border-l-yellow-500', bg: 'bg-yellow-50', text: 'text-yellow-600', dot: 'bg-yellow-500' },
    purple: { border: 'border-l-primary', bg: 'bg-primary/10', text: 'text-primary', dot: 'bg-primary' },
  };

  const config = colorConfig[color];

  return (
    <div className={`flex flex-col gap-3 rounded-xl p-6 bg-white shadow-sm border-l-4 ${config.border}`}>
      <div className="flex justify-between items-start">
        <div className={`p-2 ${config.bg} rounded-lg ${config.text}`}>
          <span className="material-symbols-outlined">{icon}</span>
        </div>
        {change !== 0 && (
          <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
            change > 0 ? 'text-green-600 bg-green-50' : 'text-slate-500 bg-slate-100'
          }`}>
            {change > 0 ? '+' : ''}{change}%
          </span>
        )}
        {change === 0 && (
          <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-2 py-1 rounded-full">0%</span>
        )}
      </div>
      <div>
        <p className="text-slate-500 text-sm font-medium">{title}</p>
        <p className="text-slate-900 text-3xl font-bold mt-1">{value}</p>
      </div>
      <div className="h-px bg-slate-100 w-full my-1"></div>
      <div className="flex justify-between text-xs font-medium text-slate-500">
        {details.map((detail, idx) => (
          <span key={idx} className={`flex items-center gap-1 ${detail.isWarning ? 'text-orange-500' : ''}`}>
            {detail.highlight && <span className={`w-2 h-2 rounded-full ${config.dot}`}></span>}
            {detail.label}: {detail.value}
          </span>
        ))}
      </div>
    </div>
  );
}

// AI Logs Loading Skeleton
function AILogsLoadingSkeleton() {
  return (
    <div className="overflow-x-auto animate-pulse">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="bg-slate-50">
            <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">시간</th>
            <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">기능</th>
            <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">토큰</th>
            <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">응답시간</th>
            <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">상태</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {[1, 2, 3, 4, 5].map((i) => (
            <tr key={i}>
              <td className="px-6 py-4"><div className="h-4 bg-slate-200 rounded w-20" /></td>
              <td className="px-6 py-4"><div className="h-5 bg-primary/10 rounded-full w-24" /></td>
              <td className="px-6 py-4"><div className="h-4 bg-slate-200 rounded w-16" /></td>
              <td className="px-6 py-4"><div className="h-4 bg-slate-200 rounded w-14" /></td>
              <td className="px-6 py-4"><div className="h-4 bg-slate-200 rounded w-12" /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
