from .models import Genre, Language

def genres_and_languages(request):
    return {
        'all_genres': Genre.objects.all()[:15],
        'all_languages': Language.objects.all(),
    }
