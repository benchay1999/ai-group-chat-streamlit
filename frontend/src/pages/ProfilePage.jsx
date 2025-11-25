/**
 * ProfilePage.jsx
 * User profile settings page with MTurk Worker ID management
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { updateMTurkWorkerId, getUserProfile } from '../services/walletAPI';
import { User, AlertCircle, CheckCircle, ArrowLeft } from 'lucide-react';
import toast from 'react-hot-toast';

const ProfilePage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [workerId, setWorkerId] = useState('');
  const [age, setAge] = useState('');
  const [gender, setGender] = useState('');
  const [nationality, setNationality] = useState('');
  const [major, setMajor] = useState('');
  const [message, setMessage] = useState({ type: '', text: '' });

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      const data = await getUserProfile();
      setProfile(data);
      setWorkerId(data.mturk_worker_id || '');
      setAge(data.age || '');
      setGender(data.gender || '');
      setNationality(data.nationality || '');
      setMajor(data.major || '');
    } catch (error) {
      console.error('Failed to fetch profile:', error);
      toast.error('Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveWorkerId = async (e) => {
    e.preventDefault();
    
    // Validate all required fields
    if (!workerId.trim()) {
      setMessage({ type: 'error', text: 'Worker ID cannot be empty' });
      return;
    }

    const ageNum = parseInt(age);
    if (!age || isNaN(ageNum) || ageNum < 18 || ageNum > 100) {
      setMessage({ type: 'error', text: 'Please enter a valid age (18-100)' });
      return;
    }

    if (!gender) {
      setMessage({ type: 'error', text: 'Please select your gender' });
      return;
    }

    if (!nationality.trim()) {
      setMessage({ type: 'error', text: 'Please enter your nationality' });
      return;
    }

    if (!major.trim()) {
      setMessage({ type: 'error', text: 'Please enter your major/field of study' });
      return;
    }

    // Basic validation for MTurk Worker ID format (alphanumeric, typically starts with A)
    const workerIdRegex = /^A[A-Z0-9]+$/;
    if (!workerIdRegex.test(workerId.trim())) {
      setMessage({ 
        type: 'error', 
        text: 'Invalid Worker ID format. MTurk Worker IDs typically start with "A" followed by alphanumeric characters.' 
      });
      return;
    }

    try {
      setSaving(true);
      setMessage({ type: '', text: '' });
      
      const result = await updateMTurkWorkerId(
        workerId.trim(), 
        ageNum, 
        gender, 
        nationality.trim(), 
        major.trim()
      );
      
      setMessage({ type: 'success', text: 'Worker ID and demographics saved successfully!' });
      toast.success('MTurk Worker ID and demographics updated!');
      
      // Refresh profile
      await fetchProfile();
      
    } catch (error) {
      console.error('Failed to save Worker ID:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to save Worker ID';
      setMessage({ type: 'error', text: errorMsg });
      toast.error(errorMsg);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        
        {/* Back Button */}
        <button
          onClick={() => navigate('/dashboard')}
          className="mb-6 flex items-center gap-2 text-gray-600 hover:text-gray-900 transition"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Dashboard
        </button>

        {/* Profile Card */}
        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="flex items-center gap-4 mb-8">
            <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center">
              <User className="w-8 h-8 text-purple-600" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Profile Settings</h1>
              <p className="text-gray-600">Manage your account information</p>
            </div>
          </div>

          {/* User Info */}
          <div className="space-y-4 mb-8">
            <div className="border-b border-gray-200 pb-4">
              <label className="text-sm font-semibold text-gray-700">Username</label>
              <p className="text-lg text-gray-900 mt-1">{user?.user_id || 'N/A'}</p>
            </div>

            <div className="border-b border-gray-200 pb-4">
              <label className="text-sm font-semibold text-gray-700">Gem Balance</label>
              <p className="text-lg text-gray-900 mt-1">
                {profile?.gem_balance?.toLocaleString() || 0} gems
                <span className="text-sm text-gray-600 ml-2">
                  (${((profile?.gem_balance || 0) / 1000).toFixed(2)} USD)
                </span>
              </p>
            </div>

            <div className="border-b border-gray-200 pb-4">
              <label className="text-sm font-semibold text-gray-700">Total Earnings</label>
              <p className="text-lg text-gray-900 mt-1">
                {profile?.total_gems_earned?.toLocaleString() || 0} gems earned
              </p>
            </div>
          </div>

          {/* MTurk Worker ID Section */}
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-2">💳 MTurk Worker ID & Demographics</h2>
            <p className="text-sm text-gray-600 mb-4">
              Required to cash out your gems. Please provide your MTurk Worker ID and demographic information. Your Worker ID can be found in your MTurk dashboard.
            </p>

            {message.text && (
              <div className={`mb-4 rounded-lg p-3 flex items-start gap-2 ${
                message.type === 'success' 
                  ? 'bg-green-50 border border-green-200' 
                  : 'bg-red-50 border border-red-200'
              }`}>
                {message.type === 'success' ? (
                  <CheckCircle className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
                )}
                <p className={`text-sm ${
                  message.type === 'success' ? 'text-green-800' : 'text-red-800'
                }`}>
                  {message.text}
                </p>
              </div>
            )}

            <form onSubmit={handleSaveWorkerId} className="space-y-4">
              {/* Age Field */}
              <div>
                <label htmlFor="age" className="block text-sm font-semibold text-gray-700 mb-2">
                  Age <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  id="age"
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  placeholder="e.g., 25"
                  min="18"
                  max="100"
                  required
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>

              {/* Gender Field */}
              <div>
                <label htmlFor="gender" className="block text-sm font-semibold text-gray-700 mb-2">
                  Gender <span className="text-red-500">*</span>
                </label>
                <select
                  id="gender"
                  value={gender}
                  onChange={(e) => setGender(e.target.value)}
                  required
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                  <option value="">Select gender...</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="wish_not_to_answer">Prefer not to answer</option>
                </select>
              </div>

              {/* Nationality Field */}
              <div>
                <label htmlFor="nationality" className="block text-sm font-semibold text-gray-700 mb-2">
                  Nationality <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="nationality"
                  value={nationality}
                  onChange={(e) => setNationality(e.target.value)}
                  placeholder="e.g., American, British, Chinese"
                  required
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>

              {/* Major Field */}
              <div>
                <label htmlFor="major" className="block text-sm font-semibold text-gray-700 mb-2">
                  Major/Field of Study <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="major"
                  value={major}
                  onChange={(e) => setMajor(e.target.value)}
                  placeholder="e.g., Computer Science, Psychology"
                  required
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>

              {/* Worker ID Field */}
              <div>
                <label htmlFor="workerId" className="block text-sm font-semibold text-gray-700 mb-2">
                  MTurk Worker ID <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="workerId"
                  value={workerId}
                  onChange={(e) => setWorkerId(e.target.value.toUpperCase())}
                  placeholder="A1BCDEFGHIJK2LMN"
                  required
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono text-sm"
                />
                <p className="mt-2 text-xs text-gray-500">
                  Find your Worker ID at: 
                  <a 
                    href="https://worker.mturk.com/dashboard" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="ml-1 text-purple-600 hover:underline"
                  >
                    worker.mturk.com/dashboard
                  </a>
                </p>
              </div>

              <button
                type="submit"
                disabled={saving || !workerId.trim() || !age || !gender || !nationality.trim() || !major.trim()}
                className={`w-full py-3 rounded-lg font-semibold transition flex items-center justify-center gap-2 ${
                  saving || !workerId.trim() || !age || !gender || !nationality.trim() || !major.trim()
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-purple-600 text-white hover:bg-purple-700'
                }`}
              >
                {saving ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    Saving...
                  </>
                ) : (
                  'Save Worker ID & Demographics'
                )}
              </button>
            </form>

            {profile?.mturk_worker_id && (
              <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-sm text-green-800 flex items-center gap-2 mb-3">
                  <CheckCircle className="w-4 h-4" />
                  <span className="font-semibold">Profile Saved</span>
                </p>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-gray-600">Worker ID:</span>
                    <p className="font-mono text-green-900">{profile.mturk_worker_id}</p>
                  </div>
                  <div>
                    <span className="text-gray-600">Age:</span>
                    <p className="text-green-900">{profile.age || 'N/A'}</p>
                  </div>
                  <div>
                    <span className="text-gray-600">Gender:</span>
                    <p className="text-green-900 capitalize">{profile.gender?.replace('_', ' ') || 'N/A'}</p>
                  </div>
                  <div>
                    <span className="text-gray-600">Nationality:</span>
                    <p className="text-green-900">{profile.nationality || 'N/A'}</p>
                  </div>
                  <div className="col-span-2">
                    <span className="text-gray-600">Major:</span>
                    <p className="text-green-900">{profile.major || 'N/A'}</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Help Section */}
          <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-semibold text-blue-900 mb-2">Need Help?</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Your Worker ID and demographics are required to receive payments via MTurk</li>
              <li>• All fields marked with * are mandatory</li>
              <li>• You can update your information anytime if you made a mistake</li>
              <li>• Make sure to enter your Worker ID correctly to avoid payment issues</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;

