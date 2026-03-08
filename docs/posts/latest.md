# AI Drug Discovery Weekly

Week of 2026-03-07

Automatically generated digest of recent research relevant to a pharma R&D workflow:

- Docking & Structure-Based Design
- QSAR & Property Prediction
- Uncertainty Quantification
- Bayesian Optimization & Active Learning
- Generative Chemistry
- Synthesis-Aware Design
- Computational Chemistry

---

## Docking & Structure-Based Design

### 1. Designing the Haystack: Programmable Chemical Space for Generative Molecular Discovery

Chemical space exploration underlies drug discovery, yet most generative models treat chemical space as a fixed, implicitly learned distribution, focusing on sampling molecules rather than deliberately designing the space itself. We introduce SpaceGFN, a generative framework that elevates chemical space to a programmable computational object: a controllable degree of freedom enabling explicit construction and adaptive traversal of structured molecular universes

[Read paper](http://arxiv.org/abs/2603.00614v1)


## QSAR & Property Prediction

### 1. MMAI Gym for Science: Training Liquid Foundation Models for Drug Discovery

General-purpose large language models (LLMs) that rely on in-context learning do not reliably deliver the scientific understanding and performance required for drug discovery tasks. Simply increasing model size or introducing reasoning tokens does not yield significant performance gains

[Read paper](http://arxiv.org/abs/2603.03517v1)

### 2. GlassMol: Interpretable Molecular Property Prediction with Concept Bottleneck Models

Machine learning accelerates molecular property prediction, yet state-of-the-art Large Language Models and Graph Neural Networks operate as black boxes. In drug discovery, where safety is critical, this opacity risks masking false correlations and excluding human expertise

[Read paper](http://arxiv.org/abs/2603.01274v1)

### 3. Benchmarking GNN Models on Molecular Regression Tasks with CKA-Based Representation Analysis

Molecules are commonly represented as SMILES strings, which can be readily converted to fixed-size molecular fingerprints. These fingerprints serve as feature vectors to train ML/DL models for molecular property prediction tasks in the field of computational chemistry, drug discovery, biochemistry, and materials science

[Read paper](http://arxiv.org/abs/2602.20573v1)

### 4. MultiPUFFIN: A Multimodal Domain-Constrained Foundation Model for Molecular Property Prediction of Small Molecules

Predicting physicochemical properties across chemical space is vital for chemical engineering, drug discovery, and materials science. Current molecular foundation models lack thermodynamic consistency, while domain-informed approaches are limited to single properties and small datasets

[Read paper](http://arxiv.org/abs/2603.00857v1)

### 5. MolFM-Lite: Multi-Modal Molecular Property Prediction with Conformer Ensemble Attention and Cross-Modal Fusion

Most machine learning models for molecular property prediction rely on a single molecular representation (either a sequence, a graph, or a 3D structure) and treat molecular geometry as static. We present MolFM-Lite, a multi-modal model that jointly encodes SELFIES sequences (1D), molecular graphs (2D), and conformer ensembles (3D) through cross-attention fusion, while conditioning predictions on experimental context via Feature-wise Linear Modulation (FiLM)

[Read paper](http://arxiv.org/abs/2602.22405v1)

### 6. Hierarchical Molecular Representation Learning via Fragment-Based Self-Supervised Embedding Prediction

Graph self-supervised learning (GSSL) has demonstrated strong potential for generating expressive graph embeddings without the need for human annotations, making it particularly valuable in domains with high labeling costs such as molecular graph analysis. However, existing GSSL methods mostly focus on node- or edge-level information, often ignoring chemically relevant substructures which strongly influence molecular properties

[Read paper](http://arxiv.org/abs/2602.20344v1)


## Uncertainty Quantification

### 1. Conformal Graph Prediction with Z-Gromov Wasserstein Distances

Supervised graph prediction addresses regression problems where the outputs are structured graphs. Although several approaches exist for graph-valued prediction, principled uncertainty quantification remains limited

[Read paper](http://arxiv.org/abs/2603.02460v3)

### 2. Learning Complex Physical Regimes via Coverage-oriented Uncertainty Quantification: An application to the Critical Heat Flux

A central challenge in scientific machine learning (ML) is the correct representation of physical systems governed by multi-regime behaviours. In these scenarios, standard data analysis techniques often fail to capture the nature of the data, as the system's response varies significantly across the state space due to its stochasticity and the different physical regimes

[Read paper](http://arxiv.org/abs/2602.21701v1)


## Bayesian Optimization & Active Learning

### 1. Bayesian Optimization in Chemical Compound Sub-Spaces using Low-Dimensional Molecular Descriptors

Efficient optimization of molecules with targeted properties remains a significant challenge due to the vast size and discrete nature of chemical compound space. Conventional machine-learning-based optimization approaches typically require large datasets to construct accurate surrogate models, limiting their applicability in data-scarce settings

[Read paper](http://arxiv.org/abs/2603.02605v1)

### 2. Deep learning-guided evolutionary optimization for protein design

Designing novel proteins with desired characteristics remains a significant challenge due to the large sequence space and the complexity of sequence-function relationships. Efficient exploration of this space to identify sequences that meet specific design criteria is crucial for advancing therapeutics and biotechnology

[Read paper](http://arxiv.org/abs/2603.02753v1)

### 3. An Active Learning Framework for Data-Efficient, Human-in-the-Loop Enzyme Function Prediction

Generalizable protein function prediction is increasingly constrained by the growing mismatch between exponentially expanding sequences of environmental proteins and the comparatively slow accumulation of experimentally verified functional data. Active learning offers a promising path forward for accelerating biological function prediction, by selecting the most informative proteins to experimentally annotate for data-efficient training, yet its potential remains largely unexplored

[Read paper](http://arxiv.org/abs/2602.23269v1)


## Computational Chemistry

### 1. MACE-POLAR-1: A Polarisable Electrostatic Foundation Model for Molecular Chemistry

Accurate modelling of electrostatic interactions and charge transfer is fundamental to computational chemistry, yet most machine learning interatomic potentials (MLIPs) rely on local atomic descriptors that cannot capture long-range electrostatic effects. We present a new electrostatic foundation model for molecular chemistry that extends the MACE architecture with explicit treatment of long-range interactions and electrostatic induction

[Read paper](http://arxiv.org/abs/2602.19411v1)

### 2. Rigidity-Aware Geometric Pretraining for Protein Design and Conformational Ensembles

Generative models have recently advanced $\textit{de novo}$ protein design by learning the statistical regularities of natural structures. However, current approaches face three key limitations: (1) Existing methods cannot jointly learn protein geometry and design tasks, where pretraining can be a solution; (2) Current pretraining methods mostly rely on local, non-rigid atomic representations for property prediction downstream tasks, limiting global geometric understanding for protein generation tasks; and (3) Existing approaches have yet to effectively model the rich dynamic and conformational information of protein structures

[Read paper](http://arxiv.org/abs/2603.02406v1)


---

Total highlighted papers: 14
