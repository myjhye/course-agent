DEFAULT_THUMBNAILS = {
    "swimming": "https://images.unsplash.com/photo-1530549387789-4c1017266635?w=800&h=450&fit=crop",
    "tennis": "https://images.unsplash.com/photo-1554068865-24cecd4e34b8?w=800&h=450&fit=crop",
    "golf": "https://images.unsplash.com/photo-1587174486073-ae5e5cff23aa?w=800&h=450&fit=crop",
    "fitness": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=800&h=450&fit=crop",
    "yoga": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=800&h=450&fit=crop",
    "pilates": "https://images.unsplash.com/photo-1518611012118-696072aa579a?w=800&h=450&fit=crop",
    "other": "https://images.unsplash.com/photo-1461896836934-bd45ba8f8e6f?w=800&h=450&fit=crop",
}


def get_default_thumbnail(sport_type: str) -> str:
    """종목에 맞는 기본 썸네일 URL 반환"""
    return DEFAULT_THUMBNAILS.get(sport_type, DEFAULT_THUMBNAILS["other"])

