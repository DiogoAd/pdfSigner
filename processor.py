from pathlib import Path
import pymupdf as fitz  # PyMuPDF


# ============================================================
# CONFIGURAÇÃO DO PDF
# ============================================================

# Página 1: posição dos "X" para o tipo de intervenção.
# Coordenadas em pontos PDF (A4 = 595 x 842).
TYPE_MARKS = {
    "CAT": (214.0, 249.5),
    "Preventiva": (314.0, 249.5),
    "Reparação": (403.0, 249.5),
    "Outro": (496.0, 249.5),  # "S. Electrica"
}

# Página 2: zonas das duas imagens.
# A linha original fica em y ~= 160.17.
# As imagens são colocadas acima dessa linha.
LEFT_IMAGE_BOX = fitz.Rect(83.62, 105.0, 251.46, 158.0)
RIGHT_IMAGE_BOX = fitz.Rect(351.13, 105.0, 518.98, 158.0)

# Página onde estão as assinaturas.
SIGNATURE_PAGE = 1       # 0-based -> página 2
TYPE_PAGE = 0            # 0-based -> página 1

# Nome da pasta onde ficam A.png, B.png e C.png,
# relativamente ao local deste processor.py.
SIGNATURES_DIR = Path(__file__).resolve().parent / "signatures"


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def get_signature_path(signature: str) -> Path:
    """
    Devolve o caminho da assinatura selecionada.

    Exemplo:
        signature="A" -> signatures/A.png
    """
    path = SIGNATURES_DIR / f"{signature}.png"

    if not path.is_file():
        raise FileNotFoundError(
            f"Não foi encontrada a assinatura '{signature}' em: {path}"
        )

    return path


def find_pngs(folder: Path) -> list[Path]:
    """
    Procura ficheiros PNG diretamente dentro da pasta.
    Não entra nas subpastas.

    O primeiro PNG encontrado é usado como imagem da pasta.
    """
    return sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() == ".png"
    )


def find_pdfs(folder: Path) -> list[Path]:
    """
    Procura PDFs diretamente dentro da pasta.
    Não entra nas subpastas.
    """
    return sorted(
        p for p in folder.iterdir()
        if p.is_file()
        and p.suffix.lower() == ".pdf"
        and not p.stem.endswith("_ASSINADO")
    )


def fit_image_in_box(image_path: Path, box: fitz.Rect) -> fitz.Rect:
    """
    Calcula um rectângulo que mantém a proporção da imagem
    e a centra dentro da caixa indicada.
    """
    image = fitz.Pixmap(str(image_path))

    if image.width <= 0 or image.height <= 0:
        raise ValueError(f"Imagem inválida: {image_path}")

    image_ratio = image.width / image.height
    box_ratio = box.width / box.height

    if image_ratio > box_ratio:
        # Imagem relativamente mais larga
        width = box.width
        height = width / image_ratio
    else:
        # Imagem relativamente mais alta
        height = box.height
        width = height * image_ratio

    x0 = box.x0 + (box.width - width) / 2
    y0 = box.y0 + (box.height - height) / 2

    return fitz.Rect(
        x0,
        y0,
        x0 + width,
        y0 + height
    )


def add_type_mark(page: fitz.Page, document_type: str) -> None:
    """
    Coloca um X no campo correspondente da página 1.
    """
    if document_type not in TYPE_MARKS:
        raise ValueError(
            f"Tipo de documento inválido: {document_type}"
        )

    x, y = TYPE_MARKS[document_type]

    page.insert_text(
        (x, y),
        "X",
        fontsize=9,
        fontname="helv",
        color=(0, 0, 0),
    )


def add_image(page: fitz.Page, image_path: Path, box: fitz.Rect) -> None:
    """
    Insere uma imagem mantendo a proporção original.
    """
    rect = fit_image_in_box(image_path, box)

    page.insert_image(
        rect,
        filename=str(image_path),
        keep_proportion=True,
    )


# ============================================================
# PROCESSAMENTO DE UM PDF
# ============================================================

def process_pdf(
    pdf_path: Path,
    png_path: Path,
    signature_path: Path,
    document_type: str,
    output_path: Path,
) -> Path:
    """
    Processa um PDF e guarda o resultado no caminho indicado.

    Não altera o PDF original.
    """

    document = fitz.open(str(pdf_path))

    try:
        if len(document) <= SIGNATURE_PAGE:
            raise ValueError(
                f"O PDF '{pdf_path.name}' não tem a página 2."
            )

        # ----------------------------------------------------
        # Página 1 - tipo de intervenção
        # ----------------------------------------------------

        type_page = document[TYPE_PAGE]
        add_type_mark(type_page, document_type)

        # ----------------------------------------------------
        # Página 2 - assinaturas
        # ----------------------------------------------------

        signature_page = document[SIGNATURE_PAGE]

        # Assinatura selecionada pelo utilizador
        add_image(
            signature_page,
            signature_path,
            LEFT_IMAGE_BOX,
        )

        # PNG encontrado na pasta do PDF
        add_image(
            signature_page,
            png_path,
            RIGHT_IMAGE_BOX,
        )

        # ----------------------------------------------------
        # Guardar novo PDF
        # ----------------------------------------------------

        document.save(
            str(output_path),
            garbage=4,
            deflate=True,
        )

    finally:
        document.close()

    return output_path


# ============================================================
# PROCESSAMENTO DE UMA PASTA
# ============================================================

def process_folder(
    root_folder: str | Path,
    document_type: str,
    signature: str,
    progress_callback=None,
) -> dict:
    """
    Percorre recursivamente a pasta escolhida.

    Cria uma nova pasta ao lado da original com o nome:
        [nome_original]_ASSINADO

    Mantém a mesma estrutura de subpastas e os mesmos
    nomes dos PDFs.

    A pasta original e os seus ficheiros não são alterados.
    """

    root = Path(root_folder)

    if not root.is_dir():
        raise NotADirectoryError(
            f"A pasta não existe ou não é válida: {root}"
        )

    # --------------------------------------------------------
    # Pasta de saída
    # --------------------------------------------------------

    output_root = root.parent / f"{root.name}_ASSINADO"

    signature_path = get_signature_path(signature)

    results = {
        "processed": [],
        "skipped": [],
        "errors": [],
    }

    # rglob("*") permite percorrer todas as subpastas.
    # Começamos também pela própria pasta escolhida.
    folders = [root] + sorted(
        p for p in root.rglob("*") if p.is_dir()
    )

    for folder in folders:

        pdfs = find_pdfs(folder)

        # Não há PDFs nesta pasta -> não há nada para fazer.
        if not pdfs:
            continue

        pngs = find_pngs(folder)

        if not pngs:
            message = (
                f"⚠ {folder.name}: "
                f"não foi encontrado nenhum PNG."
            )

            results["skipped"].append({
                "folder": folder,
                "reason": "PNG não encontrado",
            })

            if progress_callback:
                progress_callback(message)

            continue

        # Por agora usamos o primeiro PNG encontrado.
        png_path = pngs[0]

        if len(pngs) > 1 and progress_callback:
            progress_callback(
                f"⚠ {folder.name}: foram encontrados "
                f"{len(pngs)} PNGs. Será usado: {png_path.name}"
            )

        if progress_callback:
            progress_callback(
                f"📁 {folder.name}: {len(pdfs)} PDF(s) encontrado(s)."
            )

        # ----------------------------------------------------
        # Criar a mesma estrutura de pastas no destino
        # ----------------------------------------------------

        relative_folder = folder.relative_to(root)

        output_folder = output_root / relative_folder

        output_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ----------------------------------------------------
        # Processar PDFs
        # ----------------------------------------------------

        for pdf_path in pdfs:

            try:
                # Mesmo nome do PDF original
                output_path = output_folder / pdf_path.name

                process_pdf(
                    pdf_path=pdf_path,
                    png_path=png_path,
                    signature_path=signature_path,
                    document_type=document_type,
                    output_path=output_path,
                )

                results["processed"].append({
                    "input": pdf_path,
                    "output": output_path,
                })

                if progress_callback:
                    progress_callback(
                        f"✓ {pdf_path.name} → "
                        f"{output_path}"
                    )

            except Exception as exc:

                results["errors"].append({
                    "file": pdf_path,
                    "error": str(exc),
                })

                if progress_callback:
                    progress_callback(
                        f"✗ Erro em {pdf_path.name}: {exc}"
                    )

    # Guardar também a localização da pasta de saída
    results["output_folder"] = output_root

    return results


# ============================================================
# TESTE DIRETO DO PROCESSOR
# ============================================================

if __name__ == "__main__":
    print(
        "processor.py carregado.\n"
        "A lógica deve ser chamada através da interface."
    )
