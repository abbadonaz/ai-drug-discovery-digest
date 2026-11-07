"""Rebuild the entirely synthetic PDF without adding a PDF-writing dependency."""
from pathlib import Path
import textwrap


ABSTRACT = (
    "This synthetic study presents molecular prediction for drug discovery using graph models. "
    "The framework combines molecular descriptors with a learning approach for compound prioritization. "
    "The study evaluates prediction performance on a fictional benchmark for molecular screening."
)


def write_pdf(path, pages):
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    page_refs = []
    for blocks in pages:
        stream = []
        for x, y, text, width in blocks:
            lines = text.splitlines() if width is None else textwrap.wrap(text, width)
            for line in lines:
                escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                stream.append(f"BT /F1 10 Tf {x} {y} Td ({escaped}) Tj ET")
                y -= 13
        content = "\n".join(stream).encode("latin-1")
        page_id = len(objects) + 1
        page_refs.append(f"{page_id} 0 R")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {page_id+1} 0 R >>".encode())
        objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(pages)} >>".encode()
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    Path(path).write_bytes(data)


def main():
    pages = [
        [(40, 680, "Abstract", None), (40, 650, ABSTRACT, 95),
         (40, 540, "1 Introduction", None),
         (40, 510, "Molecular discovery motivates many computational approaches. This paragraph provides general background rather than demonstrating scientific performance.", 95)],
        [(40, 680, "2 Materials and\nMethods", None),
         (40, 625, "2.1 Training and Validation", None),
         (40, 595, "A graph neural network used molecular descriptors on fictional SolToy with 1000 compounds. Scaffold training and test splits were used; the protocol was retrospective, not prospective.", 43),
         (330, 680, "3 Results", None),
         (330, 650, "On the SolToy scaffold test split, RMSE decreased from 1.2 to 1.0 log mol/L versus a random forest baseline. No improvement occurred on LipToy, and no statistical significance test was reported.", 43),
         (330, 510, "3.1 Ablation Analysis", None),
         (330, 480, "Removing graph descriptors increased RMSE to 1.3 log mol/L on the same scaffold split, compared with the complete model.", 43)],
        [(40, 680, "4 Limitations", None),
         (40, 650, "No external validation or experimental binding assay was performed. Dataset bias and distribution shift limit generalization beyond the tested molecular series.", 95),
         (40, 560, "5 Discussion", None),
         (40, 530, "Table 1. RMSE on SolToy scaffold test data, comparing the graph model with the random forest baseline. Predictions are not measured biological activity.", 95),
         (40, 460, "1.0 1.2 1.3 0.8 0.9 1.1", None),
         (40, 400, "References", None),
         (40, 370, "Synthetic Author. Fictional citation only. Journal 2020, 10, 100-110. This bibliography must not enter selected scientific evidence.", 95)],
    ]
    for index, page in enumerate(pages, 1):
        page.extend([(40, 765, "SYNTHETIC FIXTURE - NOT A REAL PAPER", None), (300, 25, str(index), None)])
    write_pdf(Path(__file__).with_name("scientific-study.pdf"), pages)
    write_pdf(Path(__file__).with_name("abstract-only.pdf"), [[
        (40, 680, "Abstract", None), (40, 650, ABSTRACT, 95),
    ]])


if __name__ == "__main__":
    main()
