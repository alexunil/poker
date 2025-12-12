#!/usr/bin/env python3
"""
Quick Test für lokale Embeddings
Zeigt alle verfügbaren Provider und ihre Performance
"""

import sys
import time
from typing import Dict, Any


def test_provider(provider_name: str, **kwargs) -> Dict[str, Any]:
    """Testet einen Embedding-Provider"""
    try:
        from ai.embeddings import create_generator

        print(f"\n{'='*60}")
        print(f"Testing: {provider_name}")
        print(f"{'='*60}")

        # Erstelle Generator
        start = time.time()
        generator = create_generator(provider_name, **kwargs)
        init_time = time.time() - start
        print(f"✓ Initialization: {init_time:.2f}s")
        print(f"  Model: {generator.provider.get_model_name()}")

        # Test 1: Einzelnes Embedding
        test_text = "Implement user authentication with OAuth2 and JWT tokens"
        start = time.time()
        embedding, dimension = generator.provider.generate_embedding(test_text)
        single_time = time.time() - start

        print(f"✓ Single embedding: {single_time*1000:.0f}ms")
        print(f"  Dimension: {dimension}")
        print(f"  First 5 values: {[f'{v:.4f}' for v in embedding[:5]]}")

        # Test 2: Batch Embeddings
        test_texts = [
            "Implement user authentication",
            "Add database migration scripts",
            "Create admin dashboard",
            "Setup CI/CD pipeline",
            "Optimize query performance"
        ]

        start = time.time()
        batch_embeddings = generator.provider.batch_generate_embeddings(
            test_texts,
            show_progress=False
        )
        batch_time = time.time() - start

        print(f"✓ Batch embeddings (5 texts): {batch_time*1000:.0f}ms")
        print(f"  Avg per text: {batch_time*1000/len(test_texts):.0f}ms")
        print(f"  Speedup: {(single_time * len(test_texts)) / batch_time:.1f}x")

        # Test 3: Similarity
        emb1, _ = generator.provider.generate_embedding(test_texts[0])
        emb2, _ = generator.provider.generate_embedding(test_texts[1])
        emb_same, _ = generator.provider.generate_embedding(test_texts[0])

        sim_different = generator.cosine_similarity(emb1, emb2)
        sim_same = generator.cosine_similarity(emb1, emb_same)

        print(f"✓ Similarity test:")
        print(f"  Same text: {sim_same:.4f}")
        print(f"  Different text: {sim_different:.4f}")

        return {
            'success': True,
            'provider': provider_name,
            'init_time': init_time,
            'single_time': single_time,
            'batch_time': batch_time,
            'dimension': dimension,
            'speedup': (single_time * len(test_texts)) / batch_time
        }

    except ImportError as e:
        print(f"✗ Import Error: {e}")
        if 'sentence_transformers' in str(e):
            print("  → Install with: pip install sentence-transformers")
        return {'success': False, 'error': 'import_error'}

    except Exception as e:
        print(f"✗ Error: {e}")
        return {'success': False, 'error': str(e)}


def print_summary(results: list):
    """Zeigt Zusammenfassung aller Tests"""
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}\n")

    successful = [r for r in results if r.get('success')]

    if not successful:
        print("❌ No providers available!")
        print("\nRecommended setup:")
        print("  pip install sentence-transformers")
        return

    print(f"✓ {len(successful)} provider(s) available\n")

    # Performance-Tabelle
    print(f"{'Provider':<25} {'Init':<10} {'Single':<10} {'Batch':<10} {'Speedup':<10}")
    print("-" * 65)

    for result in successful:
        provider = result['provider']
        init = f"{result['init_time']:.2f}s"
        single = f"{result['single_time']*1000:.0f}ms"
        batch = f"{result['batch_time']*1000/5:.0f}ms"  # Per text
        speedup = f"{result['speedup']:.1f}x"

        print(f"{provider:<25} {init:<10} {single:<10} {batch:<10} {speedup:<10}")

    # Empfehlung
    print("\n" + "="*60)
    print("RECOMMENDATION")
    print("="*60)

    # Finde besten lokalen Provider
    local_providers = [r for r in successful if r['provider'] in ['sentence_transformers', 'ollama']]

    if local_providers:
        best = min(local_providers, key=lambda x: x['single_time'])
        print(f"\n✓ Best local provider: {best['provider']}")
        print(f"  Speed: {best['single_time']*1000:.0f}ms per embedding")
        print(f"  Dimension: {best['dimension']}")
        print(f"\nTo use in production:")
        print(f"  python ai/setup_ai.py process --provider {best['provider']}")
    else:
        print("\n⚠️  No local providers available!")
        print("\nQuick setup:")
        print("  pip install sentence-transformers")
        print("  python ai/setup_ai.py process --provider sentence_transformers")


def main():
    print("="*60)
    print("PLANNING POKER - LOCAL EMBEDDINGS TEST")
    print("="*60)

    results = []

    # Test sentence-transformers
    result = test_provider('sentence_transformers')
    results.append(result)

    # Test Ollama (nur wenn verfügbar)
    print(f"\n{'='*60}")
    print("Testing: ollama (optional)")
    print(f"{'='*60}")
    print("Checking if Ollama is running...")

    try:
        import urllib.request
        urllib.request.urlopen('http://localhost:11434', timeout=1)
        print("✓ Ollama server detected")
        result = test_provider('ollama')
        results.append(result)
    except:
        print("✗ Ollama not running (optional)")
        print("  → Install: https://ollama.ai")
        results.append({'success': False, 'provider': 'ollama', 'error': 'not_running'})

    # Test Mock (immer verfügbar)
    result = test_provider('mock')
    results.append(result)

    # Zusammenfassung
    print_summary(results)


if __name__ == "__main__":
    main()
