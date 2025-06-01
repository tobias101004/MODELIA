# test_extraction.py
import asyncio
import json
from pathlib import Path
from pdfminer.high_level import extract_text
from enhanced_extractors import extract_data_with_ai

async def test_extraction(pdf_path, api_key):
    print(f"Extracting text from {pdf_path}")
    
    # Extract text from PDF
    text = extract_text(pdf_path)
    print(f"Extracted {len(text)} characters")
    
    # Save text for inspection
    with open("extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print("Saved text to extracted_text.txt")
    
    # Run AI extraction
    print(f"Running AI extraction...")
    result = await extract_data_with_ai(text, api_key, "openai")
    
    # Save result
    with open("extraction_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("Saved result to extraction_result.json")
    
    # Display key fields
    if "comprador" in result:
        print("\nExtracted buyer information:")
        for key, value in result["comprador"].items():
            print(f"  {key}: {value}")
    else:
        print("No buyer information extracted!")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python test_extraction.py <pdf_path> <api_key>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    api_key = sys.argv[2]
    
    asyncio.run(test_extraction(pdf_path, api_key))
