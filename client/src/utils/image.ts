/**
 * 이미지 URL 처리 유틸리티
 * Cloudinary URL과 로컬 상대 경로를 모두 지원합니다.
 */

// VITE_API_URL이 설정되지 않았을 때를 대비한 기본값 설정
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const DEFAULT_THUMBNAIL = '/default-thumbnail.jpeg';

/**
 * 썸네일 URL을 올바른 전체 경로로 변환합니다.
 * @param url - 썸네일 URL (Cloudinary 전체 경로 또는 상대 경로)
 * @returns 완전한 이미지 URL
 */
export function getImageUrl(url: string | null | undefined): string {
  if (!url) return DEFAULT_THUMBNAIL;
  
  // 1. Cloudinary 등 전체 URL(http/https)인 경우 그대로 반환
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  
  // 2. 상대 경로인 경우 API_BASE와 안전하게 결합
  // API_BASE 끝의 /와 url 시작의 /가 겹치지 않도록 처리합니다.
  const cleanBase = API_BASE.endsWith('/') ? API_BASE.slice(0, -1) : API_BASE;
  const cleanUrl = url.startsWith('/') ? url : `/${url}`;
  
  return `${cleanBase}${cleanUrl}`;
}

/**
 * 이미지 로드 에러 핸들러
 */
export function handleImageError(e: React.SyntheticEvent<HTMLImageElement>) {
  (e.target as HTMLImageElement).src = DEFAULT_THUMBNAIL;
}