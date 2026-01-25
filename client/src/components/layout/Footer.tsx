import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="bg-slate-900 border-t border-slate-800 text-slate-400 py-12">
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-12">
          {/* Company Info */}
          <div className="col-span-1 md:col-span-1">
            <div className="flex items-center gap-2 mb-4 text-white">
              <span className="material-symbols-outlined text-primary">sports_handball</span>
              <span className="font-bold text-xl">Course Agent</span>
            </div>
            <p className="text-sm leading-relaxed mb-4">
              AI 기반 맞춤형 스포츠 강습 플랫폼<br />
              당신의 건강한 라이프스타일을 응원합니다.
            </p>
            <div className="flex gap-4">
              <a href="#" className="hover:text-white transition-colors">
                <span className="material-symbols-outlined text-[20px]">public</span>
              </a>
              <a href="#" className="hover:text-white transition-colors">
                <span className="material-symbols-outlined text-[20px]">alternate_email</span>
              </a>
              <a href="#" className="hover:text-white transition-colors">
                <span className="material-symbols-outlined text-[20px]">rss_feed</span>
              </a>
            </div>
          </div>

          {/* Platform Links */}
          <div>
            <h4 className="text-white font-bold mb-4">서비스</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link to="/lessons" className="hover:text-primary transition-colors">
                  강습 둘러보기
                </Link>
              </li>
              <li>
                <Link to="/my/enrollments" className="hover:text-primary transition-colors">
                  내 강습
                </Link>
              </li>
              <li>
                <Link to="/chat" className="hover:text-primary transition-colors">
                  AI 상담
                </Link>
              </li>
            </ul>
          </div>

          {/* Support Links */}
          <div>
            <h4 className="text-white font-bold mb-4">고객지원</h4>
            <ul className="space-y-2 text-sm">
              <li><a href="#" className="hover:text-primary transition-colors">자주 묻는 질문</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">이용약관</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">개인정보처리방침</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">문의하기</a></li>
            </ul>
          </div>

          {/* App Download */}
          <div>
            <h4 className="text-white font-bold mb-4">앱 다운로드</h4>
            <p className="text-xs mb-4">모바일에서 더 편리하게 이용하세요.</p>
            <div className="flex gap-2">
              <button className="bg-slate-800 hover:bg-slate-700 px-3 py-2 rounded-lg flex items-center gap-2 transition-colors border border-slate-700">
                <span className="material-symbols-outlined text-[18px]">android</span>
                <div className="text-left">
                  <div className="text-[8px] uppercase font-bold text-slate-400">Get it on</div>
                  <div className="text-xs font-bold text-white">Google Play</div>
                </div>
              </button>
              <button className="bg-slate-800 hover:bg-slate-700 px-3 py-2 rounded-lg flex items-center gap-2 transition-colors border border-slate-700">
                <span className="material-symbols-outlined text-[18px]">phone_iphone</span>
                <div className="text-left">
                  <div className="text-[8px] uppercase font-bold text-slate-400">Download on</div>
                  <div className="text-xs font-bold text-white">App Store</div>
                </div>
              </button>
            </div>
          </div>
        </div>

        <div className="border-t border-slate-800 pt-8 flex flex-col md:flex-row justify-between items-center text-xs">
          <p>© 2026 Course Agent Inc. All rights reserved.</p>
          <div className="flex gap-4 mt-4 md:mt-0">
            <a href="#" className="hover:text-white">개인정보</a>
            <a href="#" className="hover:text-white">이용약관</a>
            <a href="#" className="hover:text-white">쿠키정책</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
