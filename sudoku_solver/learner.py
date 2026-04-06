"""
Advanced Sudoku Learning System
- Tracks solve accuracy and verification
- Maintains solution database
- Learns improvement patterns
- Calculates confidence score
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List


class SudokuLearner:
    def __init__(self, data_dir: str = None):
        """Initialize the Sudoku Learner"""
        if data_dir is None:
            data_dir = Path(__file__).parent
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.stats_file = self.data_dir / "solver_stats_advanced.json"
        self.solutions_file = self.data_dir / "solutions_verified.json"
        
        self.stats = self._load_stats()
        self.solutions = self._load_solutions()

    def _load_stats(self) -> Dict:
        """Load statistics from file"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except:
                return self._init_stats()
        return self._init_stats()

    def _init_stats(self) -> Dict:
        """Initialize stats structure"""
        return {
            'total_solved': 0,
            'verified_correct': 0,
            'needs_review': 0,
            'accuracy_percentage': 100.0,
            'confidence_score': 0.0,
            'fastest_time': float('inf'),
            'slowest_time': 0.0,
            'avg_time': 0.0,
            'total_time': 0.0,
            'by_size': {
                '1x1': {'count': 0, 'total_time': 0, 'avg_time': 0, 'verified': 0, 'accuracy': 100.0},
                '4x4': {'count': 0, 'total_time': 0, 'avg_time': 0, 'verified': 0, 'accuracy': 100.0},
                '9x9': {'count': 0, 'total_time': 0, 'avg_time': 0, 'verified': 0, 'accuracy': 100.0},
                '16x16': {'count': 0, 'total_time': 0, 'avg_time': 0, 'verified': 0, 'accuracy': 100.0},
            },
            'last_solve': None,
            'best_accuracy_size': '9x9'
        }

    def _load_solutions(self) -> Dict:
        """Load verified solutions"""
        if self.solutions_file.exists():
            try:
                with open(self.solutions_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def record_solve(self, board_size: int, solve_time: float, moves: int, board_hash: str = None):
        """Record a solve"""
        self.stats['total_solved'] += 1
        self.stats['total_time'] += solve_time
        self.stats['avg_time'] = self.stats['total_time'] / self.stats['total_solved']
        self.stats['fastest_time'] = min(self.stats['fastest_time'], solve_time)
        self.stats['slowest_time'] = max(self.stats['slowest_time'], solve_time)
        self.stats['last_solve'] = datetime.now().isoformat()
        
        size_key = f"{board_size}x{board_size}"
        if size_key in self.stats['by_size']:
            size_stat = self.stats['by_size'][size_key]
            size_stat['count'] += 1
            size_stat['total_time'] += solve_time
            size_stat['avg_time'] = size_stat['total_time'] / size_stat['count']
        
        if board_hash:
            if board_hash not in self.solutions:
                self.solutions[board_hash] = {
                    'first_solved': datetime.now().isoformat(),
                    'solves': 0,
                    'verified_count': 0,
                    'solve_times': []
                }
            
            self.solutions[board_hash]['solves'] += 1
            self.solutions[board_hash]['solve_times'].append(solve_time)
        
        self._save_stats()

    def record_solution_accuracy(self, is_correct: bool):
        """Record if solution was verified as correct"""
        if is_correct:
            self.stats['verified_correct'] += 1
        else:
            self.stats['needs_review'] += 1
        
        total = self.stats['verified_correct'] + self.stats['needs_review']
        if total > 0:
            self.stats['accuracy_percentage'] = (self.stats['verified_correct'] / total) * 100
        
        # Update confidence
        self._update_confidence_score()
        self._save_stats()

    def _update_confidence_score(self):
        """Calculate confidence score based on accuracy and solve count"""
        accuracy = self.stats['accuracy_percentage']
        total_solves = self.stats['total_solved']
        
        # Confidence: accuracy (70%) + solve frequency (30%)
        frequency_factor = min(100, (total_solves / 10) * 100)  # Max 10 solves for 100%
        self.stats['confidence_score'] = (accuracy * 0.7) + (frequency_factor * 0.3)

    def _save_stats(self):
        """Save statistics to file"""
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
        
        with open(self.solutions_file, 'w') as f:
            json.dump(self.solutions, f, indent=2)

    def get_stats(self) -> Dict:
        """Get all statistics"""
        return self.stats

    def predict_solve_time(self, board_size: int) -> float:
        """Predict solve time based on historical data"""
        size_key = f"{board_size}x{board_size}"
        if size_key in self.stats['by_size']:
            return self.stats['by_size'][size_key].get('avg_time', 0)
        return 0

    def get_improvement_metrics(self) -> Dict:
        """Get improvement metrics"""
        return {
            'total_solves': self.stats['total_solved'],
            'accuracy': self.stats['accuracy_percentage'],
            'confidence': self.stats['confidence_score'],
            'best_size': self.stats['best_accuracy_size'],
            'improvement_potential': 100 - self.stats['accuracy_percentage']
        }
