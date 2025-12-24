import ast
from typing import Dict, Any, List


class CodeStructureAnalyzer:
    """Real code structure analyzer using Python's AST module."""
    
    async def analyze_code_patterns(self, code_segments: List[str]) -> Dict[str, Any]:
        """
        Real code pattern analysis using AST parsing.
        Detects design patterns, code metrics, and structure.
        """
        patterns_found = []
        metrics = {
            "total_functions": 0,
            "total_classes": 0,
            "async_functions": 0,
            "decorators_used": set(),
            "max_complexity": 0,
        }
        
        for segment in code_segments:
            try:
                # Parse the code into an AST
                tree = ast.parse(segment)
                
                # Walk the AST and analyze nodes
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        metrics["total_functions"] += 1
                        
                        # Count decorators
                        if node.decorator_list:
                            for dec in node.decorator_list:
                                if isinstance(dec, ast.Name):
                                    metrics["decorators_used"].add(dec.id)
                                elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                                    metrics["decorators_used"].add(dec.func.id)
                        
                        # Calculate complexity (count branches)
                        complexity = self._calculate_complexity(node)
                        metrics["max_complexity"] = max(metrics["max_complexity"], complexity)
                    
                    elif isinstance(node, ast.AsyncFunctionDef):
                        metrics["async_functions"] += 1
                        metrics["total_functions"] += 1
                        
                        if node.decorator_list:
                            for dec in node.decorator_list:
                                if isinstance(dec, ast.Name):
                                    metrics["decorators_used"].add(dec.id)
                    
                    elif isinstance(node, ast.ClassDef):
                        metrics["total_classes"] += 1
                        
                        # Detect design patterns based on class structure
                        class_name = node.name
                        
                        # Detect MVC pattern
                        if any(keyword in class_name for keyword in ["Controller", "Model", "View"]):
                            patterns_found.append("MVC")
                        
                        # Detect Factory pattern
                        if "Factory" in class_name or any(
                            isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) 
                            and method.name in ["create", "build", "make"]
                            for method in node.body
                            if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                        ):
                            patterns_found.append("Factory")
                        
                        # Detect Singleton pattern
                        if any(
                            isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and method.name == "__new__"
                            for method in node.body
                        ):
                            patterns_found.append("Singleton")
                        
                        # Detect Observer pattern
                        if any(
                            isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and method.name in ["notify", "subscribe", "unsubscribe", "update"]
                            for method in node.body
                            if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                        ):
                            patterns_found.append("Observer")
                        
                        # Check base classes for pattern detection
                        for base in node.bases:
                            if isinstance(base, ast.Name):
                                base_name = base.id
                                if "Controller" in base_name:
                                    patterns_found.append("MVC")
                                elif "Strategy" in base_name:
                                    patterns_found.append("Strategy")
                                elif "Decorator" in base_name:
                                    patterns_found.append("Decorator")
            
            except SyntaxError:
                # Skip invalid code segments
                continue
            except Exception:
                # Skip segments that cause other parsing errors
                continue
        
        # Convert set to list for JSON serialization
        metrics["decorators_used"] = sorted(list(metrics["decorators_used"]))
        
        # Remove duplicates from patterns
        patterns_found = sorted(list(set(patterns_found)))
        
        return {
            "patterns": patterns_found if patterns_found else ["Unknown"],
            "metrics": metrics,
            "is_real_analysis": True,
        }
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """
        Calculate cyclomatic complexity of a function.
        Counts decision points (if, for, while, and, or, etc.)
        """
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Count decision points
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Count logical operators (and, or)
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.ExceptHandler,)):
                complexity += 1
        
        return complexity

