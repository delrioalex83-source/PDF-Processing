import subprocess
import json
from pathlib import Path
from PIL import Image
import check_input


class PDFProcessor:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.input_dir = base_dir / "input"
        self.ocr_dir = base_dir / "ocr_output"
        self.images_dir = base_dir / "images"
        self.meta_dir = base_dir / "metadata"

        for d in (self.input_dir, self.ocr_dir, self.images_dir, self.meta_dir):
            d.mkdir(exist_ok=True)

    def run_cmd(self, cmd):
        p = subprocess.run(cmd, capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr

    def is_digital_pdf(self, pdf_path: Path) -> bool:
        """Digital PDFs have fonts. Scanned PDFs usually don't."""
        _, out, _ = self.run_cmd(["pdffonts", str(pdf_path)])
        lines = out.strip().splitlines()
        return len(lines) > 2 

    def run_ocr(self, input_pdf: Path, output_pdf: Path) -> bool:
        """
        Run OCRmyPDF, returns True if output file exists and is non empty.
        """
        cmd = [
            "ocrmypdf",
            "--skip-text",
            "--pdf-renderer", "hocr",
            "--output-type", "pdf",
            "--optimize", "0",
            "--jobs", "1",
            str(input_pdf),
            str(output_pdf),
        ]
        code, out, err = self.run_cmd(cmd)
        ok = output_pdf.exists() and output_pdf.stat().st_size > 0
        if not ok:
            print(f"[WARNING] OCRmyPDF did not produce an output PDF for {input_pdf.name}.")
            if err.strip():
                print(err.strip())
        return ok

    def extract_images(self, pdf_path: Path, pdf_stem: str):
        """
        Use pdfimages to extract embedded raster images only
        """
        raw_prefix = self.images_dir / f"{pdf_stem}_RAW_"

        # clean leftovers from previous runs
        for old in self.images_dir.glob(f"{pdf_stem}_RAW_*.png"):
            old.unlink()

        self.run_cmd(["pdfimages", "-png", str(pdf_path), str(raw_prefix)])
        raw_images = sorted(self.images_dir.glob(f"{pdf_stem}_RAW_*.png"))

        figures = []
        for idx, raw_img in enumerate(raw_images, start=1):
            new_name = f"F{idx}.png"
            new_path = self.images_dir / new_name
            try:
                img = Image.open(raw_img)
                img.save(new_path, format="PNG")
                raw_img.unlink(missing_ok=True)
            except Exception as e:
                print(f"[WARNING] Could not convert {raw_img.name}: {e}")
                continue

            figures.append({
                "figure_ID": new_name,
                "caption": "",
                "image_path": f"data/research_center/{pdf_stem}/{new_name}",
            })

        return figures

    def build_index_json(self, pdf_name: str, pdf_stem: str, figures):
        """
        Builds a JSON file and saves it as PXXXX_index.JSON.
        """
        result = {
            "paper_ID": pdf_stem,
            "access": "private",
            "paper_access": "private",

            "paper_title": "",
            "authors": [],

            "pdf_id": pdf_name,
            "pdf_path": f"data/research_center/{pdf_stem}/{pdf_name}",

            "year": None,
            "journal": "",

            "figures": figures,

            "citation": {
                "APA": ""
            }
        }

        json_path = self.meta_dir / f"{pdf_stem}_index.JSON"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        print(f"[✓] {len(figures)} figures → {json_path}")

    def ocr_only_all(self):
        """Run OCR on all PDFs in the input directory.
        Skips PDFS that already have fonts"""
        pdfs = sorted(self.input_dir.glob("*.pdf"))
        if not pdfs:
            print("No PDFs found in /input")
            return

        for pdf_path in pdfs:
            pdf_stem = pdf_path.stem
            print(f"\nOCR check → {pdf_path.name}")

            if self.is_digital_pdf(pdf_path):
                print("[WARNING] Fonts detected. No OCR needed.")
                continue

            ocr_pdf = self.ocr_dir / f"{pdf_stem}_ocr.pdf"
            print("[✓] Running OCR on PDF...")
            ok = self.run_ocr(pdf_path, ocr_pdf)
            if ok:
                print(f"[✓] OCR output → {ocr_pdf}")
            else:
                print("[ERROR] OCR failed or produced no file.")

    def extract_images_and_json_all(self):
        """Extract images and build JSON for all PDFs in the input directory."""
        pdfs = sorted(self.input_dir.glob("*.pdf"))
        if not pdfs:
            print("No PDFs found in /input")
            return

        for pdf_path in pdfs:
            pdf_stem = pdf_path.stem
            print(f"\nImages + JSON → {pdf_path.name}")

            if not self.is_digital_pdf(pdf_path):
                print("[WARNING] No fonts detected. Treating as manual.")
                #Builds an empty JSON index file with empty figures list
                self.build_index_json(pdf_path.name, pdf_stem, figures=[])
                continue

            print("[✓] Fonts detected. Extracting embedded images...")
            figures = self.extract_images(pdf_path, pdf_stem)
            self.build_index_json(pdf_path.name, pdf_stem, figures)


class ManualImageIndexer:
    """
    This class is for files already extracted from a PDF, it builds an index for every images in a folder.
    This option is to make up for the fact that this program only supports raster images with vector images having to be extracted manually.
    """
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.images_dir = base_dir / "images"
        self.meta_dir = base_dir / "metadata"
        self.images_dir.mkdir(exist_ok=True)
        self.meta_dir.mkdir(exist_ok=True)

    def build_from_images(self, paper_id: str, image_folder: Path = None):
        if image_folder is None:
            image_folder = self.images_dir

        if not image_folder.exists():
            print(f"[ERROR] Image folder does not exist: {image_folder}")
            return

        image_files = sorted(
            [p for p in image_folder.iterdir()
             if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
        )

        if not image_files:
            print(f"[WARNING] No image files found in {image_folder}")
            return

        figures = []
        for img_path in image_files:
            image_name = img_path.name
            figures.append({
                "figure_ID": image_name,
                "caption": "",
                "image_path": f"data/research_center/{paper_id}/{image_name}",
            })

        result = {
            "paper_ID": paper_id,
            "access": "private",
            "paper_access": "private",

            "paper_title": "",
            "authors": [],

            "pdf_id": f"{paper_id}.pdf",
            "pdf_path": f"data/research_center/{paper_id}/{paper_id}.pdf",

            "year": None,
            "journal": "",

            "figures": figures,

            "citation": {
                "APA": ""
            }
        }

        json_path = self.meta_dir / f"{paper_id}_index.JSON"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        print(f"[✓] Manual image index for {paper_id} → {json_path}")


def main():
    base_dir = Path.cwd()
    processor = PDFProcessor(base_dir)
    manual_indexer = ManualImageIndexer(base_dir)

    while True:
        print("\nPDF Processing Workflow:")
        print("1) Check and run OCR on PDFs in /input")
        print("2) Extract images and generate JSON for PDFs in /input")
        print("3) Generate JSON metadata from existing images (for manual extractions)")
        print("4) OCR, Image Extraction, and JSON generation (1 + 2)")
        print("5) Quit")

        choice = check_input.get_int_range("Choose an option (1-5): ", 1, 5)

        if choice == 1:
            processor.ocr_only_all()
        elif choice == 2:
            processor.extract_images_and_json_all()
        elif choice == 3:
            paper_id = input("Enter paper ID (e.g., P0010): ").strip()
            if not paper_id:
                print("[ERROR] Paper ID cannot be blank.")
                continue
            folder_str = input(
                "Image folder (press Enter for default 'images' folder): "
            ).strip()
            if folder_str:
                image_folder = Path(folder_str)
            else:
                image_folder = manual_indexer.images_dir

            manual_indexer.build_from_images(paper_id, image_folder=image_folder)
        elif choice == 4:
            processor.ocr_only_all()
            processor.extract_images_and_json_all()
        elif choice == 5:
            print("Exiting...")
            break


if __name__ == "__main__": #boilerplate code
    main()
