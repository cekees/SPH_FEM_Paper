from math import *
import proteus.MeshTools
from proteus import Domain
from proteus.default_n import *
from proteus.Profiling import logEvent
from proteus.Gauges import PointGauges, LineGauges, LineIntegralGauges

from proteus import Context

ct = Context.Options([
    ("T", 5.0, "Time interval [0, T]"),
    ("onlySaveFinalSolution",False,"Only save the final solution"),
    ("dt_fixed",0.005,"fixed time step"),
    ##################################
    ("Refinement",          4, "refinement"),
    ("StrongDirichlet",     False,"weak or strong"),
    ("use_sbm",             0,"use sbm instead of ibm"),
    ("spaceOrder",          1,"FE space for velocity"),
    ("timeOrder",           2,"1=be or 2=vbdf"),#both works, but 2 gives better cd-cl
    ("use_supg",            1.0,"Use supg or not"),
    ("nonconservative",     1.0,"0=conservative"),
    ("forceStrongDirichlet",False,"strong or weak"),
    ##################################
    ("use_ball_as_particle",1,"1 or 0 == use ball or particle"),
    ("isHotStart",False,"Use hotStart or not"),
], mutable=True)


#===============================================================================
# supg
#===============================================================================
use_supg = ct.use_supg##########
#===============================================================================
# use sbm or not
#===============================================================================
USE_SBM=ct.use_sbm
#===============================================================================
# Parameters
#===============================================================================
#  Discretization -- input options
#Refinement = 20#45min on a single core for spaceOrder=1, useHex=False
Refinement =5
sedimentDynamics=False
genMesh = True
movingDomain = False
applyRedistancing = True
useOldPETSc = False
useSuperlu = True


usePETSc = False
useSuperlu=True
parallelPartitioningType = MeshParallelPartitioningTypes.element
nLayersOfOverlapForParallel = 0

if ct.timeOrder==2:
    timeDiscretization = 'vbdf'#vbdf'#'vbdf'  # 'vbdf', 'be', 'flcbdf'
else:
    timeDiscretization = 'be'

spaceOrder = ct.spaceOrder
pspaceOrder = 1
useHex = False
useRBLES = 0.0
useMetrics = 1.0
applyCorrection = True
useVF = 0.0
useOnlyVF = False
useRANS = 0  # 0 -- None
             # 1 -- K-Epsilon
             # 2 -- K-Omega
openTop=True
fl_H = 0.40
# Input checks
if spaceOrder not in [1, 2]:
    print "INVALID: spaceOrder" + spaceOrder
    sys.exit()

if useRBLES not in [0.0, 1.0]:
    print "INVALID: useRBLES" + useRBLES
    sys.exit()

if useMetrics not in [0.0, 1.0]:
    print "INVALID: useMetrics"
    sys.exit()


weak_bc_penalty_constant = 100.0
nLevels = 1
parallelPartitioningType = proteus.MeshTools.MeshParallelPartitioningTypes.node
nLayersOfOverlapForParallel = 0

#===============================================================================
# FE space
#===============================================================================
#  Discretization
nd = 2

if spaceOrder == 1:
    hFactor = 1.0
    if useHex:
        basis = C0_AffineLinearOnCubeWithNodalBasis
        elementQuadrature = CubeGaussQuadrature(nd, 2)
        elementBoundaryQuadrature = CubeGaussQuadrature(nd - 1, 2)
    else:
        basis = C0_AffineLinearOnSimplexWithNodalBasis
        elementQuadrature = SimplexGaussQuadrature(nd, 3)
        elementBoundaryQuadrature = SimplexGaussQuadrature(nd - 1, 3)
elif spaceOrder == 2:
    hFactor = 0.5
    if useHex:
        basis = C0_AffineLagrangeOnCubeWithNodalBasis
        elementQuadrature = CubeGaussQuadrature(nd, 4)
        elementBoundaryQuadrature = CubeGaussQuadrature(nd - 1, 4)
    else:
        basis = C0_AffineQuadraticOnSimplexWithNodalBasis
        elementQuadrature = SimplexGaussQuadrature(nd, 5)
        elementBoundaryQuadrature = SimplexGaussQuadrature(nd - 1, 5)

if pspaceOrder == 1:
    if useHex:
        pbasis = C0_AffineLinearOnCubeWithNodalBasis
    else:
        pbasis = C0_AffineLinearOnSimplexWithNodalBasis
elif pspaceOrder == 2:
    if useHex:
        pbasis = C0_AffineLagrangeOnCubeWithNodalBasis
    else:
        pbasis = C0_AffineQuadraticOnSimplexWithNodalBasis


#===============================================================================
# PointGauges
#===============================================================================
# new style PointGauges
# pointGauges = PointGauges(gauges = ((('u', 'v'), ((0.5, 0.5, 0), (1, 0.5, 0))), (('p',), ((0.5, 0.5, 0),))),
#                           activeTime=(0, 0.5),
#                           sampleRate=0,
#                           fileName='combined_gauge_0_0.5_sample_all.csv')
pressure_pointGauges = PointGauges(gauges  = ((('p',), ((0.15, 0.2, 0.0),(0.25, 0.2, 0.0),),),),
                                   fileName='front_back_pressure_sample_all.csv')
# lineGauges = LineGauges(gaugeEndpoints={'lineGauge_xtoH=0.825': ((0.495, 0.0, 0.0), (0.495, 1.8, 0.0))}, linePoints=20)
# #'lineGauge_x/H=1.653':((0.99,0.0,0.0),(0.99,1.8,0.0))
# lineGauges_phi = LineGauges_phi(lineGauges.endpoints, linePoints=20)


#===============================================================================
# Domain and mesh
#===============================================================================
#L = (0.584,0.350)
L = (1, 0.4)
cpos=[0.0,0.2]
#===============================================================================
# Time stepping
#===============================================================================
T=1000
dt_fixed = 0.0005#0.03
dt_init = 0.0001#min(0.1*dt_fixed,0.001)
runCFL=0.1
dt_out=0.05
nDTout = int(round(old_div(T,dt_out)))
tnList = [0.0,dt_init]+[i*dt_out for i in range(1,nDTout+1)]

he = 1.0/2**Refinement
#he*=0.25
# he*=0.5
#he*=0.5
#he*=0.5
#he*=0.5

structured = False

if useHex:
    nnx = 4 * Refinement + 1
    nny = 2 * Refinement + 1
    hex = True
    domain = Domain.RectangularDomain(L)
else:
    boundaries = ['bottom', 'right', 'top', 'left']
    boundaryTags = dict([(key, i + 1) for (i, key) in enumerate(boundaries)])
    if structured:
        nnx = 4 * Refinement
        nny = 2 * Refinement
        domain = Domain.RectangularDomain(L)
    else:
        vertices = [[-L[0]/2., 0.0],  #0
                    [+L[0]/2., 0.0],  #1
                    [+L[0]/2., L[1]],  #2
                    [-L[0]/2., L[1]],  #3
                    [cpos[0]-0.15*L[0],L[1]*0.2],
                    [cpos[0]-0.15*L[0],L[1]*0.8],
                    [cpos[0]+0.15*L[0],L[1]*0.8],
                    [cpos[0]+0.15*L[0],L[1]*0.2],
                    # the following are set for refining the mesh
                    [cpos[0]-0.06,cpos[1]-0.06],
                    [cpos[0]-0.06,cpos[1]+0.06],
                    [cpos[0]+0.06,cpos[1]+0.06],
                    [cpos[0]+0.06,cpos[1]-0.06]]



        vertexFlags = [boundaryTags['bottom'],
                       boundaryTags['bottom'],
                       boundaryTags['top'],
                       boundaryTags['top'],
                       # the interior vertices should be flaged to 0
                       0, 0, 0, 0,
                       0, 0, 0, 0 ]

        segments = [[0, 1],
                    [1, 2],
                    [2, 3],
                    [3, 0],
                    #Interior segments
                    [4, 5],
                    [5, 6],
                    [6, 7],
                    [7,4],
                    [8,9],
                    [9,10],
                    [10,11],
                    [11,8]]
        segmentFlags = [boundaryTags['bottom'],
                        boundaryTags['right'],
                        boundaryTags['top'],
                        boundaryTags['left'],
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0]

        regions = [ [-0.48*L[0], L[1]/2.0] , [cpos[0]-0.15 , L[1]/2.0] , [cpos[0] , L[1]/2.0] ]
        regionFlags = [1,2,3]
        regionConstraints=[0.5*he**2*0.5,0.5*(he/2.0)**2,0.5*(he/4.0)**2]
        #        for gaugeName,gaugeCoordinates in pointGauges.locations.iteritems():
        #            vertices.append(gaugeCoordinates)
        #            vertexFlags.append(pointGauges.flags[gaugeName])

        # for gaugeName, gaugeLines in lineGauges.linepoints.iteritems():
        #     for gaugeCoordinates in gaugeLines:
        #         vertices.append(gaugeCoordinates)
        #         vertexFlags.append(lineGauges.flags[gaugeName])
        domain = Domain.PlanarStraightLineGraphDomain(vertices=vertices,
                                                      vertexFlags=vertexFlags,
                                                      segments=segments,
                                                      segmentFlags=segmentFlags,
                                                      regions=regions,
                                                      regionFlags=regionFlags,
                                                      regionConstraints=regionConstraints)
        #go ahead and add a boundary tags member
        domain.boundaryTags = boundaryTags
        domain.writePoly("mesh")
        domain.writePLY("mesh")
        domain.writeAsymptote("mesh")
        #triangleOptions = "VApq30Dena%8.8f" % ((he ** 2) / 2.0,)
        triangleOptions = "VApq30Dena"
        logEvent("""Mesh generated using: tetgen -%s %s""" % (triangleOptions, domain.polyfile + ".poly"))


#===============================================================================
# weak or strong Dirichlet
#===============================================================================
ns_forceStrongDirichlet = False

#===============================================================================
# Numerical parameters
#===============================================================================

ns_sed_forceStrongDirichlet = False
if useMetrics:
    ns_shockCapturingFactor  = 0.5
    ns_lag_shockCapturing = True
    ns_lag_subgridError = True
    ls_shockCapturingFactor  = 0.5
    ls_lag_shockCapturing = True
    ls_sc_uref  = 1.0
    ls_sc_beta  = 1.5
    vof_shockCapturingFactor = 0.5
    vof_lag_shockCapturing = True
    vof_sc_uref = 1.0
    vof_sc_beta = 1.5
    rd_shockCapturingFactor  = 0.5
    rd_lag_shockCapturing = False
    epsFact_density    = 1.5
    epsFact_viscosity  = epsFact_curvature  = epsFact_vof = epsFact_consrv_heaviside = epsFact_consrv_dirac = epsFact_density
    epsFact_redistance = 0.33
    epsFact_consrv_diffusion = 10.0
    redist_Newton = True
    kappa_shockCapturingFactor = 0.25
    kappa_lag_shockCapturing = True#False
    kappa_sc_uref = 1.0
    kappa_sc_beta = 1.0
    dissipation_shockCapturingFactor = 0.25
    dissipation_lag_shockCapturing = True#False
    dissipation_sc_uref = 1.0
    dissipation_sc_beta = 1.0
else:
    ns_shockCapturingFactor = 0.9
    ns_lag_shockCapturing = True
    ns_lag_subgridError = True
    ns_sed_shockCapturingFactor = 0.9
    ns_sed_lag_shockCapturing = True
    ns_sed_lag_subgridError = True
    ls_shockCapturingFactor = 0.9
    ls_lag_shockCapturing = True
    ls_sc_uref = 1.0
    ls_sc_beta = 1.0
    vof_shockCapturingFactor = 0.9
    vof_lag_shockCapturing = True
    vof_sc_uref = 1.0
    vof_sc_beta = 1.0
    vos_shockCapturingFactor = 0.9
    vos_lag_shockCapturing = True
    vos_sc_uref = 1.0
    vos_sc_beta = 1.0
    rd_shockCapturingFactor = 0.9
    rd_lag_shockCapturing = False
    epsFact_density = 1.5
    epsFact_viscosity = epsFact_curvature = epsFact_vof = epsFact_vos = epsFact_consrv_heaviside = epsFact_consrv_dirac = \
        epsFact_density
    epsFact_redistance = 0.33
    epsFact_consrv_diffusion = 0.1
    redist_Newton = False
    kappa_shockCapturingFactor = 0.9
    kappa_lag_shockCapturing = True  #False
    kappa_sc_uref = 1.0
    kappa_sc_beta = 1.0
    dissipation_shockCapturingFactor = 0.9
    dissipation_lag_shockCapturing = True  #False
    dissipation_sc_uref = 1.0
    dissipation_sc_beta = 1.0

ns_nl_atol_res = max(1.0e-10, 0.01 * he ** 2)
ns_sed_nl_atol_res = max(1.0e-10, 0.01 * he ** 2)
vof_nl_atol_res = max(1.0e-10, 0.01 * he ** 2)
vos_nl_atol_res = max(1.0e-10, 0.01 * he ** 2)
ls_nl_atol_res = max(1.0e-10, 0.01 * he ** 2)
rd_nl_atol_res = max(1.0e-10, 0.05 * he)
mcorr_nl_atol_res = max(1.0e-10, 0.01 * he ** 2)
kappa_nl_atol_res = max(1.0e-10, 0.01 * he ** 2)
dissipation_nl_atol_res = max(1.0e-10, 0.01 * he ** 2)
phi_nl_atol_res = max(1.0e-10, 0.01 * he ** 2)
pressure_nl_atol_res = max(1.0e-10, 0.01 * he ** 2)

#===============================================================================
# turbulence
#===============================================================================
ns_closure = 0  #1-classic smagorinsky, 2-dynamic smagorinsky, 3 -- k-epsilon, 4 -- k-omega
ns_sed_closure = 0  #1-classic smagorinsky, 2-dynamic smagorinsky, 3 -- k-epsilon, 4 -- k-omega
if useRANS == 1:
    ns_closure = 3
elif useRANS == 2:
    ns_closure == 4
#===============================================================================
# Water
#===============================================================================
rho_0 = 10.0
nu_0 = 0.1/rho_0

# Air
rho_1 = rho_0#1.205
nu_1 = nu_0#1.500e-5

# Sediment

rho_s = rho_0
nu_s = 10000.0*nu_0
dragAlpha = 0.0

# Surface tension
sigma_01 = 0.0

# Gravity
g = [1.0, 0.0]


# Initial condition
waterLine_x = 0.75
waterLine_z = 1.6
#===============================================================================
# used for boundary condition
#===============================================================================
U = 10 # this is the inlet max velocity not the mean velocity
def velRamp(t):
    return U
#     if t < 0.25:
#         return U*(1.0+math.cos((t-0.25)*math.pi/0.25))/2.0
#     else:
#         return U

#===============================================================================
# Use particles
#===============================================================================

def signedDistance(x):
    return x[1]-L[1]/2

def particle_sdf(t, x):
    cx = 0.2
    cy = 0.2
    r = math.sqrt( (x[0]-cx)**2 + (x[1]-cy)**2)
    n = ((x[0]-cx)/r,(x[1]-cy)/r)
    return  r - 0.05,n

def particle_vel(t, x):
    return (0.0,0.0)

#===============================================================================
# Use balls
#===============================================================================
use_ball_as_particle = ct.use_ball_as_particle
nParticles = 1
par_pos=[0.0, 0.2]
ball_center = np.array([[par_pos[0],par_pos[1],0.0],])
ball_radius = np.array([0.05,])
ball_velocity = np.array([[0.0,0.0,0.0],])
ball_angular_velocity = np.array([[0.0,0.0,0.0],])
eps=1.0e-8
def getPeriodicBC(x,tag):
    if (x[0] < -L[0]/2.0+eps or x[0] >= L[0]/2.0-eps):
        return numpy.array([0.0,
                            round(x[1],5),
                            0.0])
