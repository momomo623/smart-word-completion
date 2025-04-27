from src.app.processor import DocumentProcessor

processor = DocumentProcessor()
result = processor.process("test.docx", "output.docx")

print(result.report)
