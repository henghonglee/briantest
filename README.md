# ABB Product Search System

A probabilistic search system for matching customer queries to ABB products using supervised learning and fuzzy matching.

## Features

- **Fast TF-IDF Search**: Quick text-based search using TF-IDF embeddings
- **Probabilistic Model**: Supervised learning model trained on customer query patterns
- **Fuzzy Matching**: Handles typos and word order variations in queries
- **Large Catalog Support**: Efficiently searches through 32,000+ products
- **Incremental Training**: Add new training data to improve results

## Files Overview

- `abb_search.py` - Main search interface (command line + interactive)
- `fast_search.py` - Fast TF-IDF based search implementation
- `probabilistic_search.py` - Probabilistic model with supervised learning
- `train_model.py` - Script to train the probabilistic model
- `ABB.csv` - Product catalog (32,692 products)
- `training/` - Directory containing training data

## Quick Start

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install pandas numpy scikit-learn fuzzywuzzy python-levenshtein joblib openpyxl
```

### 2. Command Line Search

```bash
# Quick search using fast method
python abb_search.py "ACB 4P 800A circuit breaker"

# Search for contactors
python abb_search.py "contactor 400A"
```

### 3. Interactive Mode

```bash
python abb_search.py
```

Then use commands:
- `search <query>` - Search using best available method
- `fast <query>` - Use fast TF-IDF search
- `prob <query>` - Use probabilistic search (if trained)
- `train` - Train probabilistic model
- `quit` - Exit

### 4. Train Probabilistic Model (Optional)

```bash
python train_model.py
```

## Search Methods

### Fast Search (Default)
- Uses TF-IDF embeddings + fuzzy matching
- Search time: ~3ms per query
- Works immediately without training
- Good for general text matching

### Probabilistic Search
- Supervised learning on customer query patterns
- Requires training on historical data
- Better accuracy for trained query types
- Can learn customer-specific terminology

## Training Data Format

Place CSV files in `training/` directory with columns:
- `Customer Query` - Free-form customer search terms
- `Order Code` - ABB product code
- `Description` - Product description

Example:
```csv
Customer Query,Order Code,Description
ACB 4P 800A 65KA (3s),1SDA072894R1,E2.2H 800 Ekip Touch LI 4p WMP
contactor 400A,1SFL447101R1300,Contactor#AF140-40-00-13#100-250V
```

## Adding New Training Data

1. Add new CSV files to `training/` directory
2. Run `python train_model.py` to retrain
3. Or use `train` command in interactive mode

## Performance

- **Catalog Size**: 32,692 products
- **Fast Search**: ~3ms per query
- **Memory Usage**: ~50MB for embeddings
- **Training Time**: ~1 second on 745 examples

## Example Queries

The system handles various query formats:

- Technical specifications: "ACB 4P 800A 65KA"
- General terms: "circuit breaker 100A"
- Product types: "contactor", "relay protection"
- Fuzzy matches: "circut braker" → "circuit breaker"
- Mixed order: "800A ACB 4P" → finds 800A ACB products

## Architecture

1. **Text Preprocessing**: Normalize, clean, tokenize queries
2. **Feature Extraction**: TF-IDF + fuzzy string matching scores
3. **Fast Search**: Cosine similarity on pre-computed embeddings
4. **Probabilistic Model**: Random Forest trained on similarity features
5. **Result Ranking**: Probability scores for top matches

## Customization

- Modify `preprocess_text()` for domain-specific cleaning
- Adjust TF-IDF parameters in vectorizer initialization
- Change fuzzy matching weights in feature extraction
- Add new similarity features in `extract_features()`

## Troubleshooting

**Model not found**: Run `python train_model.py` first
**Slow search**: Use fast search method for large catalogs
**Poor results**: Add more training data with relevant queries
**Memory issues**: Reduce TF-IDF max_features parameter