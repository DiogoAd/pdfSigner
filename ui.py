import customtkinter as ctk
from tkinter import filedialog
from queue import Queue, Empty
import threading

from pathlib import Path
from processor import process_folder


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Inserção Automática de Imagens em PDFs")
        self.geometry("700x750")
        self.minsize(650, 650)

        # ============================
        # Variáveis
        # ============================

        self.folder_var = ctk.StringVar()
        self.document_type = ctk.StringVar(value="")
        self.signature = ctk.StringVar(value="")
        
        self.signature_options = self.get_signature_options()

        # Fila para receber mensagens do processamento
        # sem bloquear a interface.
        self.status_queue = Queue()

        # Indica se existe um processamento em curso.
        self.processing = False

        # ============================
        # Frame principal com scroll
        # ============================

        self.main_frame = ctk.CTkScrollableFrame(self)
        self.main_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        self.create_widgets()

        # Começa a verificar mensagens vindas do processor.
        self.after(100, self.process_status_queue)

    # ============================================================
    # INTERFACE
    # ============================================================
    
    def get_signature_options(self):

        signatures_dir = Path(__file__).resolve().parent / "signatures"
    
        if not signatures_dir.exists():
            return []
    
        return sorted(
            file.stem
            for file in signatures_dir.glob("*.png")
            if file.is_file()
        )

    def create_widgets(self):

        # ----------------------------
        # Título
        # ----------------------------

        title = ctk.CTkLabel(
            self.main_frame,
            text="Inserção Automática em PDFs",
            font=("Segoe UI", 24, "bold")
        )
        title.pack(pady=(20, 25))

        # ==================================================
        # Pasta
        # ==================================================

        folder_frame = ctk.CTkFrame(self.main_frame)
        folder_frame.pack(fill="x", padx=20)

        self.folder_label = ctk.CTkLabel(
            folder_frame,
            text="Pasta dos relatórios",
            font=("Segoe UI", 15, "bold")
        )
        self.folder_label.pack(
            anchor="w",
            padx=15,
            pady=(15, 5)
        )

        entry_frame = ctk.CTkFrame(
            folder_frame,
            fg_color="transparent"
        )
        entry_frame.pack(
            fill="x",
            padx=15,
            pady=(0, 15)
        )

        self.folder_entry = ctk.CTkEntry(
            entry_frame,
            textvariable=self.folder_var
        )
        self.folder_entry.pack(
            side="left",
            fill="x",
            expand=True
        )

        browse_button = ctk.CTkButton(
            entry_frame,
            text="Procurar",
            width=120,
            command=self.browse_folder
        )
        browse_button.pack(
            side="left",
            padx=(10, 0)
        )

        # ==================================================
        # Tipo de documento
        # ==================================================

        type_frame = ctk.CTkFrame(self.main_frame)
        type_frame.pack(
            fill="x",
            padx=20,
            pady=(20, 0)
        )

        self.type_label = ctk.CTkLabel(
            type_frame,
            text="Tipo de documento",
            font=("Segoe UI", 15, "bold")
        )
        self.type_label.pack(
            anchor="w",
            padx=15,
            pady=(15, 10)
        )

        options = [
            "Preventiva",
            "CAT",
            "Reparação",
            "Outro"
        ]

        for option in options:

            rb = ctk.CTkRadioButton(
                type_frame,
                text=option,
                value=option,
                variable=self.document_type,
                command=self.validate_type
            )

            rb.pack(
                anchor="w",
                padx=20,
                pady=5
            )

        # ==================================================
        # Assinatura
        # ==================================================

        signature_frame = ctk.CTkFrame(self.main_frame)
        signature_frame.pack(
            fill="x",
            padx=20,
            pady=(20, 0)
        )

        self.signature_label = ctk.CTkLabel(
            signature_frame,
            text="Assinatura",
            font=("Segoe UI", 15, "bold")
        )
        self.signature_label.pack(
            anchor="w",
            padx=15,
            pady=(15, 10)
        )
        
        for person in self.signature_options:
        
            rb = ctk.CTkRadioButton(
                signature_frame,
                text=person,
                value=person,
                variable=self.signature,
                command=self.validate_signature
            )
        
            rb.pack(
                anchor="w",
                padx=20,
                pady=5
            )
        # ==================================================
        # Botão
        # ==================================================

        self.process_button = ctk.CTkButton(
            self.main_frame,
            text="Processar PDFs",
            height=45,
            font=("Segoe UI", 15, "bold"),
            command=self.process
        )

        self.process_button.pack(pady=25)

        # ==================================================
        # Estado
        # ==================================================

        status_frame = ctk.CTkFrame(self.main_frame)
        status_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 20)
        )

        ctk.CTkLabel(
            status_frame,
            text="Estado",
            font=("Segoe UI", 15, "bold")
        ).pack(
            anchor="w",
            padx=15,
            pady=(15, 5)
        )

        self.status = ctk.CTkTextbox(
            status_frame,
            height=220
        )

        self.status.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15)
        )

        self.write_status("Aplicação pronta.")

        version_label = ctk.CTkLabel(
            self.main_frame,
            text="Versão 1.1",
            font=("Segoe UI", 10),
            text_color="gray60"
        )

        version_label.pack(
            anchor="e",
            padx=20,
            pady=(0, 20)
        )

    # ============================================================
    # VALIDAÇÃO
    # ============================================================

    def browse_folder(self):

        folder = filedialog.askdirectory()

        if folder:
            self.folder_var.set(folder)
            self.validate_folder()

    def validate_folder(self):

        normal = ("gray10", "gray90")

        if self.folder_var.get():
            self.folder_label.configure(
                text="Pasta dos relatórios",
                text_color=normal
            )

    def validate_type(self):

        normal = ("gray10", "gray90")

        if self.document_type.get():
            self.type_label.configure(
                text="Tipo de documento",
                text_color=normal
            )

    def validate_signature(self):

        normal = ("gray10", "gray90")

        if self.signature.get():
            self.signature_label.configure(
                text="Assinatura",
                text_color=normal
            )

    def validate(self):

        valid = True
        normal = ("gray10", "gray90")

        # Estado normal
        self.folder_label.configure(
            text="Pasta dos relatórios",
            text_color=normal
        )

        self.type_label.configure(
            text="Tipo de documento",
            text_color=normal
        )

        self.signature_label.configure(
            text="Assinatura",
            text_color=normal
        )

        # Pasta
        if not self.folder_var.get().strip():

            self.folder_label.configure(
                text="⚠ Pasta dos relatórios (Obrigatório)",
                text_color="red"
            )

            valid = False

        # Tipo
        if not self.document_type.get():

            self.type_label.configure(
                text="⚠ Tipo de documento (Obrigatório)",
                text_color="red"
            )

            valid = False

        # Assinatura
        if not self.signature.get():

            self.signature_label.configure(
                text="⚠ Assinatura (Obrigatório)",
                text_color="red"
            )

            valid = False

        return valid

    # ============================================================
    # LOG
    # ============================================================

    def write_status(self, text):

        self.status.configure(state="normal")
        self.status.insert("end", text + "\n")
        self.status.see("end")
        self.status.configure(state="disabled")

    def clear_status(self):

        self.status.configure(state="normal")
        self.status.delete("1.0", "end")
        self.status.configure(state="disabled")

    # ============================================================
    # PROCESSAMENTO
    # ============================================================

    def process(self):

        # Impede iniciar um segundo processamento.
        if self.processing:
            return

        # Validação dos campos obrigatórios.
        if not self.validate():
            return

        folder = self.folder_var.get().strip()
        document_type = self.document_type.get()
        signature = self.signature.get()

        # Limpa o log.
        self.clear_status()

        self.write_status("A iniciar processamento...")
        self.write_status(f"Pasta: {folder}")
        self.write_status(f"Tipo: {document_type}")
        self.write_status(f"Assinatura: {signature}")
        self.write_status("")

        # Estado da aplicação.
        self.processing = True
        self.process_button.configure(
            state="disabled",
            text="A processar..."
        )

        # Executa o processor numa thread para a UI não congelar.
        thread = threading.Thread(
            target=self.run_processor,
            args=(folder, document_type, signature),
            daemon=True
        )

        thread.start()

    def run_processor(
        self,
        folder,
        document_type,
        signature
    ):

        try:

            def progress_callback(message):
                self.status_queue.put({
                    "type": "message",
                    "value": message
                })

            results = process_folder(
                root_folder=folder,
                document_type=document_type,
                signature=signature,
                progress_callback=progress_callback
            )

            self.status_queue.put({
                "type": "finished",
                "value": results
            })

        except Exception as exc:

            self.status_queue.put({
                "type": "error",
                "value": str(exc)
            })

    # ============================================================
    # FILA DE MENSAGENS
    # ============================================================

    def process_status_queue(self):

        try:

            while True:

                message = self.status_queue.get_nowait()

                message_type = message["type"]
                value = message["value"]

                if message_type == "message":

                    self.write_status(value)

                elif message_type == "finished":

                    self.processing_finished(value)

                elif message_type == "error":

                    self.processing_error(value)

        except Empty:
            pass

        # Continua a verificar a fila.
        self.after(100, self.process_status_queue)

    # ============================================================

    def processing_finished(self, results):

        processed = len(results["processed"])
        skipped = len(results["skipped"])
        errors = len(results["errors"])

        self.write_status("")
        self.write_status("================================")
        self.write_status("PROCESSAMENTO CONCLUÍDO")
        self.write_status("================================")
        self.write_status(
            f"✓ PDFs processados: {processed}"
        )
        self.write_status(
            f"⚠ Pastas ignoradas: {skipped}"
        )
        self.write_status(
            f"✗ Erros: {errors}"
        )

        if errors == 0:
            self.write_status("")
            self.write_status(
                "Todos os PDFs foram processados com sucesso."
            )

        self.processing = False

        self.process_button.configure(
            state="normal",
            text="Processar PDFs"
        )

    # ============================================================

    def processing_error(self, error):

        self.write_status("")
        self.write_status(
            f"✗ ERRO: {error}"
        )

        self.processing = False

        self.process_button.configure(
            state="normal",
            text="Processar PDFs"
        )


if __name__ == "__main__":
    app = App()
    app.mainloop()
