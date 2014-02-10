#!/usr/bin/env python

import roslib 								#ROS Imports
roslib.load_manifest('gen2_frontier')
import rospy
from visualization_msgs.msg import Marker	#Message Imports
from geometry_msgs.msg import PoseStamped
from nav_msgs.srv import GetPlan
import math									#Other Imports
import numpy

class nodeClass():
	#Class Init Function
	def __init__(self):
		#Setup subscriber for combined searched image
		frontierMarkerSub = rospy.Subscriber('frontierMarkers',Marker,self.markerCallback,queue_size = 1) 
		
		#Get Number of Robots
		self.numRobots = rospy.get_param('/num_robots')
		
		#Setup publishers
		self.goalPub0 = rospy.Publisher('robot_0/move_base_simple/goal', PoseStamped)
		self.goalPub1 = rospy.Publisher('robot_1/move_base_simple/goal', PoseStamped)
		self.goalPub2 = rospy.Publisher('robot_2/move_base_simple/goal', PoseStamped)
		
		#Initialize Goal Publishers
		self.goalPub = []
		for i in range(0, self.numRobots):
			#Setup Subscribers to individual robot searched grids
			topicName = 'robot_' + `i` +'/move_base_simple/goal'
			self.goalPub.append(rospy.Publisher(topicName,PoseStamped))
		
		#Wait for subscribed messages to start arriving
		rospy.spin()
		
	def markerCallback(self,data):
		if len(data.points) == 0:
			print "SIMULATION COMPLETE: NO MORE FRONTIERS--Node is shutting down"
			rospy.signal_shutdown("DONE")
		else:
			#Create Cost Matrix (Cost for each robot(row)/frontier(col) pair)
			costMatrix = self.createCostMatrix(data.points)
			
			#Create Position Matrix
			posMatrix = self.createPositionMatrix(costMatrix)
			
			#Create Assign Matrix
			assignMatrix = self.createAssignmentMatrix(posMatrix)
			
			#Break Tie in Assign Matrix based on cost
			minMatrix = assignMatrix * costMatrix
			minMatrix[minMatrix == 0] = 999
			
			#Assign each robot a frontier
			frontierMin = []
			for i in range(0, self.numRobots):
				print i
				if min(minMatrix[i,:]) == 999:
					frontierMin.append(numpy.argmin(costMatrix[i,:]))
				else:
					frontierMin.append(numpy.argmin(minMatrix[i,:]))
			
			#Print for DEBUG
			print "\nCost Matrix"
			print costMatrix
			print "\nPosition Matrix"
			print posMatrix
			print "\nAssignment Matrix"
			print assignMatrix
			print "\nMin Matrix"
			print minMatrix
			
			goal = []
			#Pack messages
			for i in range(0, self.numRobots):
				goal.append(PoseStamped())
				goal[i].header.stamp = rospy.Time.now()
				goal[i].header.frame_id = '/map'
				goal[i].pose.position = data.points[frontierMin[i]]
				goal[i].pose.orientation.x = 0
				goal[i].pose.orientation.y = 0
				goal[i].pose.orientation.z = 0
				goal[i].pose.orientation.w = 1
				self.goalPub[i].publish(goal[i])
						
		
	def createAssignmentMatrix(self,P):
		tempMatrix = P.argmin(axis=0)
		assignMatrix = numpy.zeros(P.shape)
		for i in range(0,len(tempMatrix)):
			assignMatrix[tempMatrix[i],i]=1
		return assignMatrix
		
	def createPositionMatrix(self,C):
		P = numpy.zeros((C.shape[0], C.shape[1]))
		for i in range(0,C.shape[0]):
			for j in range(0, C.shape[1]):
				P[i,j] = numpy.sum(C[:,j] < C[i,j])
		return P
		
	def createCostMatrix(self,frontierPoints):
		#Make list of robots get_plan services (PUT ON PARAMATER SERVER)
		makePlanList = []
		PlanFrameId = []
		
		for i in range(0, self.numRobots):
			serviceName = '/robot_' + `i` +'/nav/move_base_node_nav/make_plan'
			frameId = '/robot_' + `i` +'/map'
			makePlanList.append(serviceName)
			PlanFrameId.append(frameId)
			
		C = numpy.zeros((len(makePlanList), len(frontierPoints)))
		
		for i in range(0,len(frontierPoints)):
			for j in range(0,len(makePlanList)):
				stop = PoseStamped()
				stop.header.frame_id = PlanFrameId[j]
				stop.pose.position = frontierPoints[i]
				serviceName = makePlanList[j]
				C[j,i] = self.determineCost(serviceName,PoseStamped(),stop)
		return C
				
		
	def determineCost(self,serviceName, start, stop):
		rospy.wait_for_service(serviceName)
		try:
			dist = 0
			makePath = rospy.ServiceProxy(serviceName, GetPlan)
			path = makePath(start, stop, 0.5)
			poseArray = path.plan.poses
			for i in range(0,len(poseArray)-1):
				xDiff = poseArray[i].pose.position.x-poseArray[i+1].pose.position.x
				yDiff = poseArray[i].pose.position.y-poseArray[i+1].pose.position.y
				dist += math.sqrt(xDiff**2+yDiff**2)
			return dist
		except rospy.ServiceException, e:
			print "Get Plan service call failed: %s" %e
			
# Main Function
if __name__ == '__main__':
	# Initialize the Node and Call nodeClass()
	rospy.init_node('frontierPlanner')
	nodeClass()
	
