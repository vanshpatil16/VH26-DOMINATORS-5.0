"""
=============================================================================
LeakGuard Edge Case Test Script
=============================================================================
PURPOSE:
  Tests the LLM fallback pipeline for external library functions that are
  intentionally ABSENT from codegate/resources.yaml.

REMOVED FROM resources.yaml (to simulate unknowns):
  1. pymongo.MongoClient  — DB client (should be: RETURNS_RESOURCE / close)
  2. httpx.Client         — HTTP client (should be: RETURNS_RESOURCE / close)
  3. h5py.File            — HDF5 file opener (should be: RETURNS_RESOURCE / close)

WHAT TO EXPECT:
  → LeakGuard AST sees the unknown library calls
  → Knowledge base lookup MISSES (not in resources.yaml)
  → LLM is queried to resolve the contract
  → LLM returns a validated contract (confidence >= 0.85)
  → Contract is auto-written back to codegate/resources.yaml
  → AST analysis proceeds with correct leak detection
  → Frontend displays: EXCEPTION LEAK / DEFINITE LEAK / SAFE correctly

HOW TO USE:
  1. Copy ALL the code from the section you want to test
  2. Paste it into the CodeGate web UI at http://localhost:3000/codegate
  3. Click "Analyze"
  4. Watch the Report, AST Tree, CFG Graph, and Trajectory tabs

=============================================================================
"""

# =============================================================================
# TEST CASE 1 — pymongo.MongoClient
# EXPECTED: EXCEPTION LEAK
# WHY: mongo_client is created. If db["users"].find() raises, close() is skipped.
# LLM should detect: pymongo.MongoClient => RETURNS_RESOURCE, close() needed
# =============================================================================

import pymongo

def fetch_user_records(host, port, query_filter):
    mongo_client = pymongo.MongoClient(host, port)          # <-- UNKNOWN to KB
    db = mongo_client["production_db"]
    results = list(db["users"].find(query_filter))          # Can raise!
    mongo_client.close()                                    # Only reached if no exception
    return results


# =============================================================================
# TEST CASE 2 — httpx.Client
# EXPECTED: DEFINITE LEAK
# WHY: http_client is never closed — no close() anywhere in the function.
# LLM should detect: httpx.Client => RETURNS_RESOURCE, close() needed
# =============================================================================

import httpx

def download_payload(url, headers):
    http_client = httpx.Client(timeout=10)                  # <-- UNKNOWN to KB
    response = http_client.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None
    # http_client.close() is NEVER called -- DEFINITE LEAK


# =============================================================================
# TEST CASE 3 — h5py.File
# EXPECTED: EXCEPTION LEAK
# WHY: hdf5_file is opened. If dataset processing raises, file is never closed.
# LLM should detect: h5py.File => RETURNS_RESOURCE, close() needed
# =============================================================================

import h5py
import numpy as np

def process_hdf5_dataset(filepath, dataset_name, threshold):
    hdf5_file = h5py.File(filepath, "r")                   # <-- UNKNOWN to KB
    dataset = hdf5_file[dataset_name]
    values = dataset[:]                                     # Can raise KeyError/IOError
    result = values[values > threshold].mean()              # Can raise ValueError
    hdf5_file.close()
    return float(result)


# =============================================================================
# COMBINED TEST -- paste this single function to test all 3 together
# EXPECTED: MULTIPLE LEAKS detected
# =============================================================================

def combined_edge_case_test(mongo_host, api_url, hdf5_path):
    """Tests all 3 unknown library functions in one analyzer run."""

    # --- pymongo ---
    mongo_client = pymongo.MongoClient(mongo_host, 27017)   # UNKNOWN #1
    records = list(mongo_client["mydb"]["logs"].find({}))   # Can raise

    # --- httpx ---
    http_client = httpx.Client()                            # UNKNOWN #2
    resp = http_client.get(api_url)                         # Can raise
    data = resp.json()

    # --- h5py ---
    hdf5_file = h5py.File(hdf5_path, "r")                  # UNKNOWN #3
    arr = hdf5_file["matrix"][:]                            # Can raise

    # Only one resource gets closed properly:
    mongo_client.close()

    # http_client => DEFINITE LEAK (never closed)
    # hdf5_file  => EXCEPTION LEAK (close only if no exception above)
    hdf5_file.close()

    return records, data, arr.tolist()
