package store

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/vcscsvcscs/ai-book-translator/internal/model"
)

type Store struct {
	baseDir string
	mu      sync.Mutex
}

func New(dataDir string) *Store {
	return &Store{baseDir: dataDir}
}

func (s *Store) projectDir(id string) string {
	return filepath.Join(s.baseDir, id)
}

func (s *Store) projectFile(id string) string {
	return filepath.Join(s.projectDir(id), "project.json")
}

func (s *Store) Create(p *model.Project) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if p.ID == "" {
		p.ID = uuid.New().String()
	}
	now := time.Now()
	p.CreatedAt = now
	p.UpdatedAt = now
	if p.Status == "" {
		p.Status = model.StatusCreated
	}

	dir := s.projectDir(p.ID)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return fmt.Errorf("create project dir: %w", err)
	}

	return s.writeProject(p)
}

func (s *Store) Save(p *model.Project) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	p.UpdatedAt = time.Now()
	return s.writeProject(p)
}

func (s *Store) Load(id string) (*model.Project, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	return s.readProject(id)
}

func (s *Store) List() ([]*model.Project, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	entries, err := os.ReadDir(s.baseDir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}

	var projects []*model.Project
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		p, err := s.readProject(e.Name())
		if err != nil {
			continue
		}
		projects = append(projects, p)
	}

	sort.Slice(projects, func(i, j int) bool {
		return projects[i].UpdatedAt.After(projects[j].UpdatedAt)
	})

	return projects, nil
}

func (s *Store) Delete(id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	dir := s.projectDir(id)
	if _, err := os.Stat(dir); os.IsNotExist(err) {
		return fmt.Errorf("project %s not found", id)
	}
	return os.RemoveAll(dir)
}

func (s *Store) ProjectDir(id string) string {
	return s.projectDir(id)
}

func (s *Store) writeProject(p *model.Project) error {
	data, err := json.MarshalIndent(p, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal project: %w", err)
	}
	return os.WriteFile(s.projectFile(p.ID), data, 0o644)
}

func (s *Store) readProject(id string) (*model.Project, error) {
	data, err := os.ReadFile(s.projectFile(id))
	if err != nil {
		return nil, fmt.Errorf("read project %s: %w", id, err)
	}
	p := &model.Project{}
	if err := json.Unmarshal(data, p); err != nil {
		return nil, fmt.Errorf("unmarshal project %s: %w", id, err)
	}
	return p, nil
}
