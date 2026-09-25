import webbrowser
import sys

def abrir_link(url: str) -> None:
    """
    Abre a URL informada no navegador padrão.
    """
    try:
        webbrowser.open(url, new_tab=True)
        print(f"✅ Link aberto: {url}")
    except Exception as e:
        print(f"❌ Não foi possível abrir o link: {e}")

if __name__ == "__main__":
    # Se o usuário passou o link como argumento
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # Caso contrário, pede interativamente
        url = input("🔗 Digite o link que deseja abrir: ").strip()

    if url:
        abrir_link(url)
    else:
        print("⚠️  Nenhum link foi informado.")