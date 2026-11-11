// Package polish turns raw Whisper output into developer-ready text: a
// developer-flavored initial prompt, deterministic cleanup, and an optional
// local LLM pass.
package polish

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
	"unicode"

	"github.com/yuribodo/vox/internal/asr"
)

// DeveloperPrompt is Whisper's initial context. Whisper copies the spelling and
// punctuation of its prompt, so it is written as developer speech, not a list.
const DeveloperPrompt = "Let's review the code in the useEffect hook, then push it to GitHub. " +
	"Run npm install, check the .env file and api/routes.ts, and open a PR. " +
	"I'm using Claude Code, TypeScript, React, Next.js, Node.js, Python, Go, Docker, kubectl, PostgreSQL, JSON, YAML, and the CLI."

// Rule replaces a misheard phrase with the wanted spelling.
type Rule struct {
	heard  *regexp.Regexp
	wanted string
}

// DefaultRules are unambiguous developer mishearings. Ambiguous ones such as
// "quote" for "code" need context and are left to the LLM pass.
var DefaultRules = mustRules(`
git hub => GitHub
git lab => GitLab
type script => TypeScript
java script => JavaScript
node js => Node.js
next js => Next.js
vue js => Vue.js
cube control => kubectl
cube cuddle => kubectl
kube control => kubectl
pie test => pytest
post gres => Postgres
postgres sql => PostgreSQL
dot env => .env
whisper flow => Wispr Flow
whisperflow => Wispr Flow
clock code => Claude Code
clod code => Claude Code
cloud code => Claude Code
`)

var (
	sentenceFiller = regexp.MustCompile(`(?i)(^|[.!?]\s+)(?:uh+|um+|uhm+|erm)\b[,.]?\s*(\p{Ll})`)
	filler         = regexp.MustCompile(`(?i)\s*\b(?:uh+|um+|uhm+|erm)\b[,.]?`)
	sentence       = regexp.MustCompile(`[^.!?]+[.!?]*\s*`)
	spaces         = regexp.MustCompile(`[ \t]{2,}`)
)

// Clean removes fillers and Whisper repetition loops, then applies rules.
func Clean(text string, rules []Rule) string {
	text = sentenceFiller.ReplaceAllStringFunc(text, func(match string) string {
		parts := sentenceFiller.FindStringSubmatch(match)
		return parts[1] + strings.ToUpper(parts[2])
	})
	text = filler.ReplaceAllString(text, "")
	text = dropRepeatedSentences(text)
	for _, rule := range rules {
		text = rule.heard.ReplaceAllLiteralString(text, rule.wanted)
	}
	return strings.TrimSpace(spaces.ReplaceAllString(text, " "))
}

// dropRepeatedSentences removes a sentence identical to the one before it,
// the signature of a Whisper decoding loop. Short ones ("No. No.") stay.
func dropRepeatedSentences(text string) string {
	var kept strings.Builder
	previous := ""
	for _, part := range sentence.FindAllString(text, -1) {
		key := strings.Join(words(part), " ")
		if key == previous && strings.Count(key, " ") >= 3 {
			continue
		}
		previous = key
		kept.WriteString(part)
	}
	return kept.String()
}

// words splits text into lowercase letter/number runs.
func words(text string) []string {
	return strings.FieldsFunc(strings.ToLower(text), func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsNumber(r)
	})
}

// ParseRules reads "heard => wanted" lines; blank lines and # comments are skipped.
func ParseRules(r io.Reader) ([]Rule, error) {
	var rules []Rule
	scanner := bufio.NewScanner(r)
	for line := 1; scanner.Scan(); line++ {
		text := strings.TrimSpace(scanner.Text())
		if text == "" || strings.HasPrefix(text, "#") {
			continue
		}
		heard, wanted, ok := strings.Cut(text, "=>")
		words := strings.Fields(heard)
		wanted = strings.TrimSpace(wanted)
		if !ok || len(words) == 0 || wanted == "" {
			return nil, fmt.Errorf("line %d: want \"heard => wanted\"", line)
		}
		for i, word := range words {
			words[i] = regexp.QuoteMeta(word)
		}
		pattern := strings.Join(words, `[\s-]+`)
		if isWord(heard[strings.IndexFunc(heard, notSpace)]) {
			pattern = `\b` + pattern
		}
		if trimmed := strings.TrimSpace(heard); isWord(trimmed[len(trimmed)-1]) {
			pattern += `\b`
		}
		rules = append(rules, Rule{heard: regexp.MustCompile(`(?i)` + pattern), wanted: wanted})
	}
	return rules, scanner.Err()
}

func notSpace(r rune) bool { return !unicode.IsSpace(r) }

func isWord(b byte) bool {
	return b == '_' || b >= '0' && b <= '9' || b >= 'a' && b <= 'z' || b >= 'A' && b <= 'Z'
}

func mustRules(text string) []Rule {
	rules, err := ParseRules(strings.NewReader(text))
	if err != nil {
		panic(err)
	}
	return rules
}

// LoadRules reads a user rules file; a missing file yields no rules.
func LoadRules(path string) ([]Rule, error) {
	file, err := os.Open(path)
	if errors.Is(err, os.ErrNotExist) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	defer file.Close()
	rules, err := ParseRules(io.LimitReader(file, 64*1024))
	if err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	return rules, nil
}

// ConfigDir is $XDG_CONFIG_HOME/vox, falling back to ~/.config/vox.
func ConfigDir() string {
	if dir := os.Getenv("XDG_CONFIG_HOME"); filepath.IsAbs(dir) {
		return filepath.Join(dir, "vox")
	}
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".config", "vox")
}

// Transcriber wraps Whisper with the developer prompt and cleanup passes.
type Transcriber struct {
	Inner          asr.Transcriber
	VocabularyPath string
	Rules          []Rule
	LLM            *LLM
	// Warn receives LLM failures; the cleaned Whisper text is used instead.
	Warn func(error)
}

func (t Transcriber) Transcribe(ctx context.Context, request asr.Request) (asr.Result, error) {
	if request.Prompt == "" {
		request.Prompt = DeveloperPrompt
	}
	if request.HotwordsPath == "" && t.VocabularyPath != "" {
		if _, err := os.Stat(t.VocabularyPath); err == nil {
			request.HotwordsPath = t.VocabularyPath
		}
	}
	result, err := t.Inner.Transcribe(ctx, request)
	if err != nil {
		return result, err
	}
	result.Text = Clean(result.Text, t.Rules)
	if t.LLM != nil && result.Text != "" {
		started := time.Now()
		polished, err := t.LLM.Polish(ctx, result.Text)
		result.Latency += time.Since(started)
		if err != nil {
			if t.Warn != nil {
				t.Warn(err)
			}
		} else {
			result.Text = polished
		}
	}
	return result, nil
}
