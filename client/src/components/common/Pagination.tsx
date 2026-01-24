interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export default function Pagination({ page, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;

  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    const showPages = 5;
    
    let start = Math.max(1, page - Math.floor(showPages / 2));
    let end = Math.min(totalPages, start + showPages - 1);
    
    if (end - start < showPages - 1) {
      start = Math.max(1, end - showPages + 1);
    }
    
    if (start > 1) {
      pages.push(1);
      if (start > 2) pages.push('...');
    }
    
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    
    if (end < totalPages) {
      if (end < totalPages - 1) pages.push('...');
      pages.push(totalPages);
    }
    
    return pages;
  };

  return (
    <div className="flex items-center justify-center gap-1 mt-6">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className="px-3 py-2 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
      >
        이전
      </button>
      
      {getPageNumbers().map((p, idx) => (
        <button
          key={idx}
          onClick={() => typeof p === 'number' && onPageChange(p)}
          disabled={p === '...'}
          className={`px-3 py-2 rounded-lg text-sm ${
            p === page
              ? 'bg-blue-600 text-white'
              : p === '...'
              ? 'cursor-default'
              : 'hover:bg-gray-100'
          }`}
        >
          {p}
        </button>
      ))}
      
      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        className="px-3 py-2 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
      >
        다음
      </button>
    </div>
  );
}

