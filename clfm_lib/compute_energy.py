import numpy as np

def computeEnergy(X,Xd,Vxf, nargout=2):
    """
     Syntax:

           [V Vdot] = computeEnergy(X,Xd,Vxf)

     This function computes the energy value at query point(s) X, given the energy
     (Lyapunov) function Vxf. When Xd is passed as an empty variable, it also
     provides the energy gradient (i.e. Vdot = dV). Otherwise, it computes the
     rate of change in energy by moving along Xd.

     Inputs -----------------------------------------------------------------
       o X:       d x N matrix representing N different query point(s)

       o Xd:      d x N matrix representing the velocities at the query points.
                  Note that Xd could also be passed as an empty variable.
                  Xd is used to compute the rate of change in the energy by
                  moving along the velocity vector, i.e. Vdot = dV/dx . dx/dt.
                  If Xd = [], then Vdot = dV/dx is given as the output

       o Vxf:     A structure variable representing the energy function. This
                  structure should follow the format explained in learnEnergy.m

     Outputs ----------------------------------------------------------------

       o V:       A 1 x N array representing the energy values at the query points.

       o Vdot:    A 1 x N array representing the rate of change in energy at
                  the query points by moving along the velocity vector Xd.
                  When Xd is passed as an empty variable, then it is d x N
                  matrix, where each column corresponds to the energy gradient
                  (i.e. Vdot = dV) at each query point.


             Copyright (c) 2014 Mohammad Khansari, LASA Lab, EPFL,
              CH-1015 Lausanne, Switzerland, http://lasa.epfl.ch


     The program is free for non-commercial academic use. Please contact the
     author if you are interested in using the software for commercial purposes.
     The software must not be modified or distributed without prior permission
     of the authors. Please acknowledge the authors in any academic publications
     that have made use of this code or part of it. Please use this BibTex
     reference:

     S.M. Khansari-Zadeh and A. Billard (2014), "Learning Control Lyapunov Function
     to Ensure Stability of Dynamical System-based Robot Reaching Motions."
     Robotics and Autonomous Systems, vol. 62, num 6, p. 752-765.

     To get latest update of the software please visit
                              http://cs.stanford.edu/people/khansari/

     Please send your feedbacks or questions to:
                              khansari_at_cs.stanford.edu

    Ported to Python by Lekan Ogunmolu
                        August 2017
                        patlekano@gmail.com
    """
    # print(X.shape)
    d = X.shape[0]
    nDemo = 1 #X.shape[2]
    # print('nDemo: ', nDemo)
    if nDemo>1:
        X = X.reshape(d,-1)
        Xd = Xd.reshape(d,-1)

    if Vxf['SOS']:
        V, dV = sos_lyapunov(X, Vxf['P'], Vxf['d'], Vxf['n'])
        if 'p0' in Vxf:
            V -= Vxf['p0']
    else:
        V, dV = gmr_lyapunov(X, Vxf['Priors'], Vxf['Mu'], Vxf['P'])

    # print('nargout: ', nargout, nDemo)
    if nargout > 1:
        if not Xd.size:
            Vdot = dV
        else:
            Vdot = np.sum(Xd*dV, axis=0)
    if nDemo>1:
        V = V.reshape(-1, nDemo).T
        if nargout > 1:
            Vdot = Vdot.reshape(-1, nDemo).T

    return V, Vdot


def gmr_lyapunov(x, Priors, Mu, P):
    # print('x.shape: ', x.shape)
    nbData = x.shape[1]
    d = x.shape[0]
    L = P.shape[2]-1;

    # Compute the influence of each GMM component, given input x
    for k in range(L):
        P_cur               = P[:,:,k+1]
        if k                == 0:
            # print('V: ', V)
            # print('P_cur: ', P_cur, x.shape)
            # print('Priors[k+1]: ', Priors, Priors[k+1])
            V_k             = np.sum(x * (P_cur.dot(x)), axis=0)
            V               = Priors[k+1] * V_k
            Vx              = Priors[k+1] * ((P_cur+P_cur.T).dot(x))
        else:
            x_tmp           = x - np.tile(Mu[:,k+1], [nbData, 1]).T
            #  x_tmp.shape will be (2,750)
            V_k             = np.sum(P_cur.dot(x_tmp)*x, axis=0)
            V_k[V_k < 0]    = 0
            # Prios will be of shape (1,)
            V              += Priors[k+1].dot(np.expand_dims(V_k ** 2, axis=0))
            # (V_k).shape)) == (750,)
            temp            = (2 * Priors[k+1]).dot(np.expand_dims(V_k, axis=0))
            # temp will be of shape (750,)
            # Vx will be of shape (2,750)
            Vx              = Vx + np.tile(temp, [d,1])*(P_cur.dot(x_tmp) + P_cur.T.dot(x))
            # print('Vx shape: ', Vx.shape)
    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    #These lines are for adding some spaces between the contour lines
    #         beta = zeros(size(V_k));
    #         dbeta = zeros(size(V_k));
    #         thr = 10000000;
    #         tau = pi/thr;
    #         ind_1 = ((V_k < thr) & (V_k > 0));
    #         ind_2 = V_k >= thr;
    #         beta(ind_1) = -0.5*sin(-tau*V_k(ind_1)+pi/2)+0.5;
    #         beta(ind_2) = 1;
    #         dbeta(ind_1) = 0.5*tau*cos(-tau*V_k(ind_1)+pi/2);
    #
    #         V = V + Priors(k+1)*beta.*(V_k).^2;#alpha.*w.*V_k;
    #         Vx = Vx + repmat(2*Priors(k+1)*beta.*V_k,d,1).*(invP*x+ invP'*x_tmp);
    #         Vx(:,ind_1) = Vx(:,ind_1) + repmat(Priors(k+1)*dbeta(ind_1).*V_k(ind_1).^2,d,1).*(invP*x(:,ind_1)+ invP'*x_tmp(:,ind_1));
    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    #         PP_k = 2*(x'*invP*x)*invP + 2*(x_tmp'*invP*x_tmp)*invP + ...
    #                4*invP*(x_tmp*x' + x*x_tmp')*invP + ...
    #                2*d_alpha_d_sc*invP*(V_k*(x_tmp*(x_tmp + x)' + (x_tmp + x)*x_tmp') +...
    #                w*(x*(x_tmp + x)' + (x_tmp + x)*x'))*invP;
    #         PP = PP + Priors(k)*PP_k;%*alpha;

    return V, Vx
