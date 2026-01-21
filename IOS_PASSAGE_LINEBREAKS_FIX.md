# Passage Content Line Break Rendering

## The Reality

**Passages have NO line breaks in the database.** Content is stored as continuous text. The web app wraps to 50 characters client-side.

## Exact Web Logic (JavaScript)

This is the **exact** algorithm the web app uses. Port this 1:1 to Swift:

```javascript
function formatPassageForSAT(content) {
    // Step 1: Normalize literal \n strings (just in case)
    if (typeof content === 'string') {
        content = content.replace(/\\\\n/g, '\n');
        content = content.replace(/\\n/g, '\n');
    }
    
    const allLines = [];
    
    // Step 2: Split by double newlines = paragraphs
    const paragraphs = content.split(/\n\n+/);
    
    paragraphs.forEach((paragraph, paraIndex) => {
        // Step 3: Split by single newlines = original lines
        const originalLines = paragraph.split(/\n/);
        
        originalLines.forEach(originalLine => {
            const trimmed = originalLine.trim();
            
            if (!trimmed) {
                allLines.push('');  // Preserve blank lines
                return;
            }
            
            // Step 4: Wrap to 50 characters
            const words = trimmed.split(/\s+/);
            let currentLine = '';
            
            words.forEach(word => {
                const testLine = currentLine ? currentLine + ' ' + word : word;
                if (testLine.length <= 50) {
                    currentLine = testLine;
                } else {
                    if (currentLine) {
                        allLines.push(currentLine);
                    }
                    // Handle words longer than 50 chars
                    if (word.length > 50) {
                        let remaining = word;
                        while (remaining.length > 50) {
                            allLines.push(remaining.substring(0, 50));
                            remaining = remaining.substring(50);
                        }
                        currentLine = remaining;
                    } else {
                        currentLine = word;
                    }
                }
            });
            
            if (currentLine) {
                allLines.push(currentLine);
            }
        });
        
        // Add blank line between paragraphs (not after last)
        if (paraIndex < paragraphs.length - 1) {
            allLines.push('');
        }
    });
    
    // Step 5: Add line numbers (skip blank lines in count)
    let lineNumber = 0;
    const linesWithNumbers = allLines.map(line => {
        const isBlank = !line || line.trim() === '';
        if (!isBlank) {
            lineNumber++;
        }
        return {
            text: line,
            isBlank: isBlank,
            lineNumber: isBlank ? null : lineNumber
        };
    });
    
    // Step 6: Show line number every 5 lines (5, 10, 15, 20...)
    // Only on non-blank lines
    return linesWithNumbers;
}
```

## Swift Port (Exact Same Logic)

```swift
struct PassageLine {
    let text: String
    let isBlank: Bool
    let lineNumber: Int?  // nil for blank lines
}

func formatPassageForSAT(_ content: String) -> [PassageLine] {
    // Step 1: Normalize literal \n strings
    var normalized = content
        .replacingOccurrences(of: "\\\\n", with: "\n")
        .replacingOccurrences(of: "\\n", with: "\n")
    
    var allLines: [String] = []
    
    // Step 2: Split by double newlines = paragraphs
    let paragraphs = normalized.components(separatedBy: try! NSRegularExpression(pattern: "\\n\\n+").splitString(normalized))
    // Simpler: just split by "\n\n"
    let paragraphsSimple = normalized.components(separatedBy: "\n\n")
    
    for (paraIndex, paragraph) in paragraphsSimple.enumerated() {
        // Step 3: Split by single newlines
        let originalLines = paragraph.components(separatedBy: "\n")
        
        for originalLine in originalLines {
            let trimmed = originalLine.trimmingCharacters(in: .whitespaces)
            
            if trimmed.isEmpty {
                allLines.append("")
                continue
            }
            
            // Step 4: Wrap to 50 characters
            let words = trimmed.components(separatedBy: .whitespaces).filter { !$0.isEmpty }
            var currentLine = ""
            
            for word in words {
                let testLine = currentLine.isEmpty ? word : currentLine + " " + word
                
                if testLine.count <= 50 {
                    currentLine = testLine
                } else {
                    if !currentLine.isEmpty {
                        allLines.append(currentLine)
                    }
                    // Handle words longer than 50 chars
                    if word.count > 50 {
                        var remaining = word
                        while remaining.count > 50 {
                            let index = remaining.index(remaining.startIndex, offsetBy: 50)
                            allLines.append(String(remaining[..<index]))
                            remaining = String(remaining[index...])
                        }
                        currentLine = remaining
                    } else {
                        currentLine = word
                    }
                }
            }
            
            if !currentLine.isEmpty {
                allLines.append(currentLine)
            }
        }
        
        // Add blank line between paragraphs (not after last)
        if paraIndex < paragraphsSimple.count - 1 {
            allLines.append("")
        }
    }
    
    // Step 5: Add line numbers (skip blank lines in count)
    var lineNumber = 0
    return allLines.map { line in
        let isBlank = line.trimmingCharacters(in: .whitespaces).isEmpty
        if !isBlank {
            lineNumber += 1
        }
        return PassageLine(
            text: line,
            isBlank: isBlank,
            lineNumber: isBlank ? nil : lineNumber
        )
    }
}
```

## SwiftUI View

```swift
struct SATPassageView: View {
    let content: String
    
    private var lines: [PassageLine] {
        formatPassageForSAT(content)
    }
    
    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            ForEach(Array(lines.enumerated()), id: \.offset) { _, line in
                HStack(alignment: .top, spacing: 8) {
                    // Line number column (show every 5th)
                    if let num = line.lineNumber, num % 5 == 0 {
                        Text("\(num)")
                            .font(.system(size: 11))
                            .foregroundColor(.secondary)
                            .frame(width: 20, alignment: .trailing)
                    } else {
                        Spacer().frame(width: 20)
                    }
                    
                    // Line text
                    if line.isBlank {
                        Spacer().frame(height: 16)  // Paragraph gap
                    } else {
                        Text(line.text)
                            .font(.custom("Georgia", size: 15))
                    }
                }
            }
        }
    }
}
```

## Key Rules

| Rule | Value |
|------|-------|
| Max line width | **50 characters** |
| Line numbers shown | Every **5th line** (5, 10, 15...) |
| Blank lines | **Don't count** in line numbering |
| Paragraph breaks | Insert **1 blank line** between |
| Long words (>50 chars) | **Hard split** at 50 |
