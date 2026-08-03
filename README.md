# Software & Graphics Portfolio

A curated collection of nine standalone projects spanning real-time graphics,
interactive simulation, systems programming, and object-oriented application
design. Each project links directly to its source and supporting documentation.

[Featured Projects](#featured-projects) · [Project Index](#project-index) ·
[Getting Started](#getting-started) · [License](#license)

## Featured Projects

| | |
| --- | --- |
| [![Embervault procedural environment](<Interactive Graphics/Embervault/screenshots/preview.png>)](<Interactive Graphics/Embervault/README.md>) | [![Aether Reactor particle simulation](<Interactive Graphics/Aether Reactor/screenshots/preview.png>)](<Interactive Graphics/Aether Reactor/README.md>) |
| **[Embervault](<Interactive Graphics/Embervault/README.md>)**<br>Procedural first-person environment with generated mazes, textured geometry, lighting, fog, spatial audio, and an objective-driven game loop.<br><sub>Python · Pygame · PyOpenGL</sub> | **[Aether Reactor](<Interactive Graphics/Aether Reactor/README.md>)**<br>GPU-assisted particle system with multiple emitter modes, force fields, real-time controls, and custom GLSL shaders.<br><sub>Python · Pygame · PyOpenGL · NumPy · GLSL</sub> |
| [![Atomic Resonance visualization](<Interactive Graphics/Atomic Resonance/screenshots/preview.png>)](<Interactive Graphics/Atomic Resonance/README.md>) | [![LightForge mesh renderer](<Interactive Graphics/LightForge/screenshots/preview.png>)](<Interactive Graphics/LightForge/README.md>) |
| **[Atomic Resonance](<Interactive Graphics/Atomic Resonance/README.md>)**<br>Interactive atomic-structure visualization with orbital motion, electron transitions, and photon-emission effects.<br><sub>Python · Pygame · PyOpenGL</sub> | **[LightForge](<Interactive Graphics/LightForge/README.md>)**<br>Real-time mesh renderer featuring OBJ loading, generated normals, configurable lighting, and GLSL shading modes.<br><sub>Python · Pygame · PyOpenGL · GLSL</sub> |

## Project Index

### Interactive Graphics

| Project | Technical Focus | Core Stack |
| --- | --- | --- |
| [Polyhedral Atlas](<Interactive Graphics/Polyhedral Atlas/README.md>) | Platonic-solid construction, topology, duality, and interactive inspection | Python, Pygame, PyOpenGL |
| [Helios Orrery](<Interactive Graphics/Helios Orrery/README.md>) | Hierarchical transforms, orbital animation, camera tracking, and time controls | Python, Pygame, PyOpenGL |
| [LightForge](<Interactive Graphics/LightForge/README.md>) | OBJ parsing, generated normals, lighting models, and shader pipelines | Python, Pygame, PyOpenGL, GLSL |
| [Crystal Dice Foundry](<Interactive Graphics/Crystal Dice Foundry/README.md>) | Textured polyhedra, quaternion rotation, collision response, and dice motion | Python, Pygame, PyOpenGL |
| [Embervault](<Interactive Graphics/Embervault/README.md>) | Procedural maze generation, first-person navigation, lighting, fog, and audio | Python, Pygame, PyOpenGL |
| [Atomic Resonance](<Interactive Graphics/Atomic Resonance/README.md>) | Atomic structure, orbital dynamics, state transitions, and photon effects | Python, Pygame, PyOpenGL |
| [Aether Reactor](<Interactive Graphics/Aether Reactor/README.md>) | Particle emitters, force fields, GPU rendering, and real-time parameter control | Python, Pygame, PyOpenGL, NumPy, GLSL |

### C++ Applications

| Project | Technical Focus | Core Stack |
| --- | --- | --- |
| [Key Management System](<A Key Management System>) | File-backed key inventory with employee lookup, assignment, returns, and state export | C++, STL, file I/O |
| [Tamagotchi Pet Game](<Tamagotchi Pet Game>) | Polymorphic virtual pets with species-specific actions, evolving state, and save/load persistence | C++, inheritance, polymorphism, file I/O |

## Technical Focus

- **Real-time rendering:** camera systems, mesh processing, lighting, textures,
  transparency, and GLSL shaders.
- **Simulation:** orbital hierarchies, particle fields, collision response, and
  state-driven animation.
- **Procedural systems:** connected maze generation, dynamic environments, and
  repeatable runtime controls.
- **Software design:** modular architecture, object-oriented models, persistence,
  and file-backed state management.

## Getting Started

Clone the collection and open the project you want to explore:

```bash
git clone https://github.com/agrovr/CollegeProjects.git
cd CollegeProjects
```

Each interactive graphics directory contains its own README with dependencies,
installation steps, launch commands, and controls. The C++ applications contain
standalone source directories; the Tamagotchi Pet Game targets Windows.

## License

This repository is distributed under the
[GNU General Public License v3.0](LICENSE) and maintained by
[agrovr](https://github.com/agrovr).
