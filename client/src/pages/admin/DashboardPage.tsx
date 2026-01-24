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

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [aiLogs, setAILogs] = useState<AILog[]>([]);
  const [loading, setLoading] = useState(true);
  const [aiLogsLoading, setAiLogsLoading] = useState(true);
  const [logFilter, setLogFilter] = useState<string>('');

  useEffect(() => {
    loadDashboard();
    loadAILogs(); // 별도로 로드
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
    return <div className="p-4">로딩 중...</div>;
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">운영 대시보드</h1>

      {/* 기간 정보 */}
      <p className="text-sm text-gray-500">
        기간: {new Date(stats.period.start_date).toLocaleDateString('ko-KR')} ~{' '}
        {new Date(stats.period.end_date).toLocaleDateString('ko-KR')}
      </p>

      {/* 주요 지표 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 강습 현황 */}
        <StatCard
          title="강습"
          value={stats.lessons.total}
          unit="개"
          color="blue"
          details={[
            { label: '발행됨', value: stats.lessons.published },
            { label: '초안', value: stats.lessons.draft },
          ]}
        />

        {/* 수강 현황 */}
        <StatCard
          title="수강생"
          value={stats.enrollments.total}
          unit="명"
          color="green"
          details={[
            { label: '신규 (기간)', value: stats.enrollments.new_in_period },
            { label: '수료 (기간)', value: stats.enrollments.completed_in_period },
          ]}
        />

        {/* 평균 출석률 */}
        <StatCard
          title="평균 출석률"
          value={stats.enrollments.avg_attendance_rate}
          unit="%"
          color="yellow"
          details={[
            { label: '수강 중', value: stats.enrollments.in_progress },
            { label: '수료', value: stats.enrollments.completed },
          ]}
        />

        {/* AI 사용량 */}
        <StatCard
          title="AI 호출"
          value={stats.ai_usage.total_calls}
          unit="회"
          color="purple"
          details={[
            { label: '평균 응답', value: `${stats.ai_usage.avg_latency_ms}ms` },
            { label: '수정률', value: `${stats.ai_usage.edit_rate}%` },
          ]}
        />
      </div>

      {/* AI 기능별 사용량 */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-bold mb-4">AI 기능별 사용량</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(stats.ai_usage.by_feature).map(([feature, count]) => (
            <div
              key={feature}
              className="bg-gray-50 rounded-lg p-4 text-center"
            >
              <div className="text-2xl font-bold text-purple-600">{count}</div>
              <div className="text-sm text-gray-500 mt-1">
                {FEATURE_LABELS[feature] || feature}
              </div>
            </div>
          ))}
        </div>
        {stats.ai_usage.total_tokens > 0 && (
          <p className="text-sm text-gray-400 mt-4 text-right">
            총 토큰 사용량: {stats.ai_usage.total_tokens.toLocaleString()}
          </p>
        )}
      </div>

      {/* 종목별 강습 분포 */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-bold mb-4">종목별 강습</h2>
        <div className="flex flex-wrap gap-3">
          {Object.entries(stats.lessons.by_sport).map(([sport, count]) => (
            <div
              key={sport}
              className="bg-blue-50 text-blue-700 px-4 py-2 rounded-lg"
            >
              {SPORT_LABELS[sport] || sport}: <span className="font-bold">{count}</span>개
            </div>
          ))}
        </div>
      </div>

      {/* AI 로그 */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold">최근 AI 로그</h2>
            {aiLogsLoading && (
              <div className="flex items-center gap-2 text-sm text-purple-600">
                <div className="w-4 h-4 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
                <span>로드 중...</span>
              </div>
            )}
          </div>
          <select
            value={logFilter}
            onChange={(e) => setLogFilter(e.target.value)}
            className="text-sm border border-gray-300 rounded-lg px-3 py-1.5"
            disabled={aiLogsLoading}
          >
            <option value="">전체</option>
            {Object.entries(FEATURE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {aiLogsLoading ? (
          <AILogsLoadingSkeleton />
        ) : aiLogs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">로그가 없습니다.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">시간</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">기능</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">토큰</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">응답시간</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">수정됨</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {aiLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {new Date(log.created_at).toLocaleString('ko-KR')}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                        {FEATURE_LABELS[log.feature_type] || log.feature_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700">
                      {log.tokens_used?.toLocaleString() || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700">
                      {log.latency_ms ? `${Math.round(log.latency_ms)}ms` : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {log.was_edited ? (
                        <span className="text-orange-600">수정됨</span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// AI 로그 로딩 스켈레톤
function AILogsLoadingSkeleton() {
  return (
    <div className="overflow-x-auto animate-pulse">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">시간</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">기능</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">토큰</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">응답시간</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">수정됨</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {[1, 2, 3, 4, 5].map((i) => (
            <tr key={i}>
              <td className="px-4 py-3">
                <div className="h-4 bg-gray-200 rounded w-32" />
              </td>
              <td className="px-4 py-3">
                <div className="h-5 bg-purple-100 rounded w-20" />
              </td>
              <td className="px-4 py-3">
                <div className="h-4 bg-gray-200 rounded w-16" />
              </td>
              <td className="px-4 py-3">
                <div className="h-4 bg-gray-200 rounded w-14" />
              </td>
              <td className="px-4 py-3">
                <div className="h-4 bg-gray-200 rounded w-10" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// 통계 카드 컴포넌트
function StatCard({
  title,
  value,
  unit,
  color,
  details,
}: {
  title: string;
  value: number | string;
  unit: string;
  color: 'blue' | 'green' | 'yellow' | 'purple';
  details: { label: string; value: number | string }[];
}) {
  const colorClasses = {
    blue: 'text-blue-600',
    green: 'text-green-600',
    yellow: 'text-yellow-600',
    purple: 'text-purple-600',
  };

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-sm font-medium text-gray-500 mb-2">{title}</h3>
      <div className="flex items-baseline gap-1 mb-4">
        <span className={`text-3xl font-bold ${colorClasses[color]}`}>
          {value}
        </span>
        <span className="text-gray-500">{unit}</span>
      </div>
      <div className="space-y-1">
        {details.map((detail, idx) => (
          <div key={idx} className="flex justify-between text-sm">
            <span className="text-gray-500">{detail.label}</span>
            <span className="font-medium text-gray-700">{detail.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

